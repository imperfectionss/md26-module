"""L'appel de modele du module MD-26.

Un seul endroit pour : plusieurs fournisseurs, la reprise avec attente
croissante, le comptage des tokens et du cout, la bascule de secours, la
capture et le mode hors ligne.

Ecrit une fois au TP0 bis, utilise jusqu'au TP11. Python 3.10 ou plus.

Aucun nom de fournisseur n'est ecrit dans ce fichier. Ils vivent dans .env,
parce que les offres gratuites changent plus vite qu'un support de cours.
Presque tous exposent une API compatible avec le meme format de messages ;
c'est ce que ce client utilise.

.env attendu
------------
    FOURNISSEUR_PRINCIPAL=nom_court     le developpement
    FOURNISSEUR_SECOURS=autre_nom       la bascule, obligatoire
    FOURNISSEUR_MESURE=troisieme_nom    les mesures de mesure.py
    FOURNISSEUR_GRANDE_FENETRE=nom      appele par son nom (TP2, TP1 bis)

    LLM_NOM_COURT_URL=https://.../v1/chat/completions
    LLM_NOM_COURT_CLE=...
    LLM_NOM_COURT_MODELE=...
    LLM_NOM_COURT_PRIX_ENTREE=0.10      dollars par million de tokens
    LLM_NOM_COURT_PRIX_SORTIE=0.40
    LLM_NOM_COURT_PRIX_CACHE=0.05       tokens d'entree lus dans le cache
    LLM_NOM_COURT_MAX_TOKENS=2048       facultatif : plafond de la reponse
    LLM_NOM_COURT_OPTIONS={"cle": 1}    facultatif : champs JSON ajoutes a
                                        chaque requete de ce fournisseur

MAX_TOKENS compte chez Groq : sa limite par minute additionne le prompt et le
plafond de reponse demande, et une requete sans plafond peut etre refusee.
OPTIONS sert aux reglages propres a un fournisseur, par exemple
{"thinking": {"type": "disabled"}} chez Z.ai, ou le raisonnement de GLM est
actif par defaut et ralentit chaque appel.

Sans PRIX_CACHE, un token lu dans le cache est compte a la moitie du prix
d'entree : c'est la remise que Groq affiche pour gpt-oss (documentation
« Prompt caching », relevee le 25 septembre 2026). Les autres fournisseurs
ont leur propre remise : renseignez-la.

Utilisation
-----------
    from client_llm import Client

    client = Client()                          principal, secours automatique
    client = Client(fournisseur="zai")         un fournisseur precis, sans secours
    client = Client(hors_ligne=True)           rejeu, sans reseau
    client = Client(capturer="hors_ligne/moi") chaque reponse est enregistree

    reponse = client.appeler(messages, outils=mes_outils)
    print(reponse.texte, reponse.cout, reponse.tokens_entree)

Les memes reglages par l'environnement, ce que fait mesure.py :
    MD26_HORS_LIGNE=1              rejeu
    MD26_CAPTURER=hors_ligne/moi   capture
    MD26_FOURNISSEUR=zai           un seul fournisseur, sans secours
    MD26_REJEU_STRICT=1            le rejeu refuse les captures d'un autre modele
"""

from __future__ import annotations

import email.utils
import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from hors_ligne import Capture, Rejeu


# --------------------------------------------------------------------------

class ErreurFournisseur(RuntimeError):
    """Le fournisseur a repondu une erreur qu'il ne sert a rien de reessayer."""


class QuotaDuFournisseur(ErreurFournisseur):
    """Un fournisseur annonce un quota epuise pour `pause` secondes."""

    def __init__(self, message: str, pause: float) -> None:
        super().__init__(message)
        self.pause = pause


class QuotaEpuise(RuntimeError):
    """Tous les fournisseurs configures ont refuse. Passez en hors ligne."""


@dataclass
class Reponse:
    texte: str
    appels_outils: list[dict] = field(default_factory=list)
    tokens_entree: int = 0
    tokens_sortie: int = 0
    tokens_caches: int = 0
    cout: float = 0.0
    latence: float = 0.0
    fournisseur: str = ""
    modele: str = ""
    # Le message du modele, a remettre tel quel dans la conversation avant les
    # resultats d'outils (chapitre 3, §3.4). Nettoye : seuls role, content et
    # tool_calls, parce que certains fournisseurs refusent en entree les champs
    # qu'ils ajoutent en sortie.
    message_brut: dict = field(default_factory=dict)

    @property
    def demande_un_outil(self) -> bool:
        return bool(self.appels_outils)


# --------------------------------------------------------------------------

def charger_env(chemin: Path | None = None) -> None:
    """Lit .env sans dependance supplementaire. Ne remplace pas l'existant."""
    chemin = chemin or Path(".env")
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


def _prefixe(nom: str) -> str:
    return f"LLM_{nom.upper().replace('-', '_')}_"


def _prix(variable: str) -> float | None:
    valeur = os.environ.get(variable, "")
    return float(valeur) if valeur.strip() else None


@dataclass
class Fournisseur:
    nom: str
    url: str
    cle: str
    modele: str
    prix_entree: float = 0.0      # dollars par million de tokens
    prix_sortie: float = 0.0
    prix_cache: float = 0.0
    max_tokens: int | None = None
    options: dict = field(default_factory=dict)

    @classmethod
    def depuis_env(cls, nom: str, sans_cle: bool = False) -> "Fournisseur":
        """sans_cle : pour le rejeu, qui n'a besoin que du nom du modele."""
        p = _prefixe(nom)
        exiges = ("MODELE",) if sans_cle else ("URL", "CLE", "MODELE")
        manquants = [p + s for s in exiges if not os.environ.get(p + s)]
        if manquants:
            raise ErreurFournisseur(
                f"Fournisseur '{nom}' incomplet dans .env. Manque : "
                f"{', '.join(manquants)}")
        entree = _prix(p + "PRIX_ENTREE") or 0.0
        cache = _prix(p + "PRIX_CACHE")
        plafond = os.environ.get(p + "MAX_TOKENS", "").strip()
        brut = os.environ.get(p + "OPTIONS", "").strip()
        try:
            options = json.loads(brut) if brut else {}
        except json.JSONDecodeError as e:
            raise ErreurFournisseur(f"{p}OPTIONS n'est pas du JSON valide : {e}")
        if not isinstance(options, dict):
            raise ErreurFournisseur(f"{p}OPTIONS doit etre un objet JSON {{...}}")
        return cls(
            nom=nom,
            url=os.environ.get(p + "URL", ""),
            cle=os.environ.get(p + "CLE", ""),
            modele=os.environ[p + "MODELE"],
            prix_entree=entree,
            prix_sortie=_prix(p + "PRIX_SORTIE") or 0.0,
            prix_cache=entree / 2 if cache is None else cache,
            max_tokens=int(plafond) if plafond else None,
            options=options,
        )

    def cout(self, entree: int, sortie: int, caches: int = 0) -> float:
        """Les tokens caches font partie des tokens d'entree, a un autre prix."""
        caches = min(caches, entree)
        return ((entree - caches) * self.prix_entree
                + caches * self.prix_cache
                + sortie * self.prix_sortie) / 1_000_000


def lire_retry_after(valeur: str | None) -> float | None:
    """L'en-tete Retry-After : des secondes, ou une date HTTP."""
    if not valeur:
        return None
    try:
        return max(0.0, float(valeur))
    except ValueError:
        pass
    try:
        date = email.utils.parsedate_to_datetime(valeur)
    except (TypeError, ValueError):
        return None
    return max(0.0, date.timestamp() - time.time())


# --------------------------------------------------------------------------

class Client:
    """Le client d'appel. Une instance par agent.

    Le journal est ecrit dans journal/payload.jsonl : c'est la matiere du
    TP0 bis, et la trace dont le bloc 10 fera une instrumentation. Il contient
    le corps de chaque requete et de chaque reponse, jamais les en-tetes, donc
    jamais la cle.
    """

    ESSAIS_MAX = 5
    ATTENTE_INITIALE = 1.0
    ATTENTE_MAX = 32.0
    # Au-dela, le fournisseur parle d'un quota, pas d'un encombrement : on
    # bascule au lieu d'attendre (§6.6.3).
    RETRY_AFTER_MAX = 60.0

    def __init__(self, fournisseur: str | None = None, hors_ligne: bool = False,
                 journal: Path | None = Path("journal/payload.jsonl"),
                 simuler_429: bool = False,
                 capturer: str | Path | None = None) -> None:
        charger_env()
        explicite = fournisseur is not None
        if fournisseur is None and os.environ.get("MD26_FOURNISSEUR"):
            fournisseur = os.environ["MD26_FOURNISSEUR"]

        self.hors_ligne = hors_ligne or os.environ.get("MD26_HORS_LIGNE") == "1"
        self.simuler_429 = simuler_429
        self.journal = journal
        self._en_pause: dict[str, float] = {}
        self._429_restants = 2 if simuler_429 else 0
        # Un fournisseur nomme par l'appelant, ou par mesure.py --fournisseur,
        # ne rejoue que ses propres captures (TP1 bis : A et B distincts).
        self._strict = explicite or os.environ.get("MD26_REJEU_STRICT") == "1"

        dossier = capturer or os.environ.get("MD26_CAPTURER")
        self.capture = Capture(Path(dossier)) if dossier and not self.hors_ligne else None

        if self.hors_ligne:
            self.rejeu = Rejeu()
            self.chaine: list[Fournisseur] = []
            nom = fournisseur or os.environ.get("FOURNISSEUR_PRINCIPAL") or ""
            self._rejoue: Fournisseur | None = None
            if nom:
                try:
                    self._rejoue = Fournisseur.depuis_env(nom, sans_cle=True)
                except ErreurFournisseur:
                    self._rejoue = None
            return

        self.rejeu = None
        noms = [fournisseur] if fournisseur else [
            os.environ.get("FOURNISSEUR_PRINCIPAL"),
            os.environ.get("FOURNISSEUR_SECOURS"),
        ]
        noms = [n for n in noms if n]
        if not noms:
            raise ErreurFournisseur(
                "Aucun fournisseur configure. Renseignez FOURNISSEUR_PRINCIPAL "
                "dans .env, puis lancez python verifier.py.")
        if len(noms) == 1 and not fournisseur:
            print("  Un seul fournisseur configure. Le module en demande deux : "
                  "une offre gratuite peut fermer ou changer en cours de semestre.")
        self.chaine = [Fournisseur.depuis_env(n) for n in noms]

    # ----------------------------------------------------------------------

    def appeler(self, messages: list[dict], outils: list[dict] | None = None,
                temperature: float = 0.0, **extra) -> Reponse:
        """Un appel. Bascule sur le secours si le principal refuse."""
        if self.hors_ligne:
            self._subir_429_simules("hors_ligne")
            return self._rejouer(messages, outils)

        derniere: Exception | None = None
        # Un fournisseur qui vient de dire « quota epuise » n'est pas rappele
        # a chaque requete : il est saute jusqu'a la fin de la pause, sauf
        # s'il ne reste que lui.
        maintenant = time.time()
        chaine = [f for f in self.chaine
                  if self._en_pause.get(f.nom, 0) <= maintenant] or self.chaine
        for fournisseur in chaine:
            try:
                return self._appeler_un(fournisseur, messages, outils,
                                        temperature, extra)
            except (ErreurFournisseur, requests.RequestException) as erreur:
                derniere = erreur
                if isinstance(erreur, QuotaDuFournisseur):
                    self._en_pause[fournisseur.nom] = time.time() + erreur.pause
                if fournisseur is not chaine[-1]:
                    print(f"  {fournisseur.nom} refuse ({erreur}). "
                          f"Bascule sur le secours.")
        raise QuotaEpuise(
            f"Tous les fournisseurs ont refuse. Derniere erreur : {derniere}. "
            f"Relancez plus tard, ou avec --hors-ligne.")

    # ----------------------------------------------------------------------

    def _pause(self, attente: float, conseil: float | None) -> float:
        """Attente croissante, plus un peu de hasard, et au moins ce que le
        fournisseur demande. Sans le hasard, trente machines de la salle
        reessaient a la meme seconde."""
        pause = min(attente, self.ATTENTE_MAX)
        if conseil is not None:
            pause = max(pause, conseil)
        return pause + random.uniform(0, 0.5)

    def _subir_429_simules(self, nom: str) -> None:
        """--simuler-429 : deux refus avant le vrai appel, en ligne comme en
        rejeu. Le premier annonce un Retry-After d'une seconde."""
        attente = self.ATTENTE_INITIALE
        essai = 0
        while self._429_restants > 0:
            self._429_restants -= 1
            essai += 1
            pause = self._pause(attente, 1.0 if essai == 1 else None)
            print(f"  429 simule sur {nom}, attente {pause:.1f}s "
                  f"(essai {essai}/{self.ESSAIS_MAX})")
            time.sleep(pause)
            attente *= 2

    def _appeler_un(self, f: Fournisseur, messages: list[dict],
                    outils: list[dict] | None, temperature: float,
                    extra: dict) -> Reponse:
        charge = {"model": f.modele, "messages": messages,
                  "temperature": temperature}
        if f.max_tokens:
            charge["max_tokens"] = f.max_tokens
        # Les reglages du fournisseur, puis ceux de l'appel, qui l'emportent.
        charge.update(f.options)
        charge.update(extra)
        if outils:
            charge["tools"] = outils

        debut = time.perf_counter()
        self._subir_429_simules(f.nom)
        attente = self.ATTENTE_INITIALE

        for essai in range(1, self.ESSAIS_MAX + 1):
            r = requests.post(
                f.url,
                headers={"Authorization": f"Bearer {f.cle}",
                         "Content-Type": "application/json"},
                json=charge, timeout=120)
            statut = r.status_code
            try:
                corps = r.json()
            except ValueError:
                corps = {"error": r.text[:300]}

            if statut == 200:
                reponse = self._lire(corps, f)
                reponse.latence = time.perf_counter() - debut
                self._journaliser(charge, corps, reponse)
                if self.capture is not None:
                    self.capture.ajouter(messages, outils, corps,
                                         f.nom, f.modele)
                return reponse

            if statut == 401:
                raise ErreurFournisseur(
                    f"401 sur {f.nom} : cle absente, fausse ou expiree. "
                    f"Reessayer ne sert a rien.")

            if statut == 429 or statut >= 500:
                conseil = lire_retry_after(r.headers.get("Retry-After"))
                if conseil is not None and conseil > self.RETRY_AFTER_MAX:
                    raise QuotaDuFournisseur(
                        f"{statut} sur {f.nom}, Retry-After de {conseil:.0f}s : "
                        f"quota epuise pour l'instant", conseil)
                if essai == self.ESSAIS_MAX:
                    raise ErreurFournisseur(f"{statut} apres {essai} essais")
                pause = self._pause(attente, conseil)
                print(f"  {statut} sur {f.nom}, attente {pause:.1f}s "
                      f"(essai {essai}/{self.ESSAIS_MAX})")
                time.sleep(pause)
                attente *= 2
                continue

            raise ErreurFournisseur(f"{statut} : {str(corps)[:200]}")

        raise ErreurFournisseur("essais epuises")

    # ----------------------------------------------------------------------

    @staticmethod
    def _lire(corps: dict, f: Fournisseur) -> Reponse:
        choix = (corps.get("choices") or [{}])[0]
        message = choix.get("message", {})
        usage = corps.get("usage", {}) or {}
        details = usage.get("prompt_tokens_details", {}) or {}

        entree = int(usage.get("prompt_tokens", 0))
        sortie = int(usage.get("completion_tokens", 0))
        caches = int(details.get("cached_tokens", 0) or 0)

        appels = []
        for appel in message.get("tool_calls") or []:
            fonction = appel.get("function", {})
            arguments = fonction.get("arguments", "{}")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"_brut": arguments}
            appels.append({"id": appel.get("id"),
                           "nom": fonction.get("name"),
                           "arguments": arguments})

        brut = {"role": "assistant", "content": message.get("content")}
        if message.get("tool_calls"):
            brut["tool_calls"] = message["tool_calls"]
        # Gemini 3, par sa couche compatible, joint une signature de pensee
        # qu'il faut lui renvoyer telle quelle au tour suivant.
        if message.get("extra_content"):
            brut["extra_content"] = message["extra_content"]

        return Reponse(
            texte=message.get("content") or "",
            appels_outils=appels,
            message_brut=brut,
            tokens_entree=entree,
            tokens_sortie=sortie,
            tokens_caches=caches,
            cout=f.cout(entree, sortie, caches),
            fournisseur=f.nom,
            modele=f.modele,
        )

    def _rejouer(self, messages: list[dict], outils: list[dict] | None) -> Reponse:
        assert self.rejeu is not None
        f = self._rejoue
        brut = self.rejeu.chercher(
            messages, outils,
            fournisseur=f.nom if f else "", modele=f.modele if f else "",
            strict=self._strict)
        # Le cout rejoue est celui des tokens de la capture, aux prix de votre
        # .env : il se lit, il ne se mesure pas.
        prix = f or Fournisseur(nom="hors_ligne", url="", cle="", modele="rejeu")
        reponse = self._lire(brut, prix)
        reponse.fournisseur = f"hors_ligne:{prix.nom}"
        reponse.latence = 0.0        # une latence rejouee ne veut rien dire
        return reponse

    def _journaliser(self, charge: dict, corps: dict, reponse: Reponse) -> None:
        if not self.journal:
            return
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        with self.journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "horodatage": time.time(),
                "fournisseur": reponse.fournisseur,
                "modele": reponse.modele,
                "envoye": charge,          # le payload REEL. C'est le TP0 bis.
                "recu": corps,
                "tokens_entree": reponse.tokens_entree,
                "tokens_sortie": reponse.tokens_sortie,
                "tokens_caches": reponse.tokens_caches,
                "cout": reponse.cout,
                "latence": reponse.latence,
            }, ensure_ascii=False) + "\n")
