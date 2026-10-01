"""Le banc de mesure du module MD-26.

Lance un agent sur un jeu de taches, plusieurs fois, et rend ses nombres.

Il arrive au TP1 et sert jusqu'au TP11. C'est la piece a ecrire en premier :
onze feuilles de TP en dependent, et sans lui la mesure n'arriverait qu'au
bloc 10, apres huit TP qui auront conclu "ca marche".

Utilisation
-----------
    python mesure.py --agent sanad --taches taches/b1.jsonl --repetitions 3 --sortie mesures/b1.json
    python mesure.py --agent sanad --taches taches/b1.jsonl --limite 5 --repetitions 1
    python mesure.py --agent sanad --taches taches/b1.jsonl --capturer
    python mesure.py --agent sanad --taches taches/b1.jsonl --hors-ligne --seuil 0.6

Les options du banc
-------------------
    --sortie FICHIER     la mesure en JSON, en UTF-8. Jamais « --json > fichier »
                         sous Windows PowerShell, qui ecrit en UTF-16
    --limite N           seulement les N premieres taches (le developpement)
    --fournisseur NOM    le fournisseur de la mesure, sans secours. Par defaut,
                         FOURNISSEUR_MESURE du fichier .env. Nomme ici, il
                         rend le rejeu strict : seulement ses propres captures
    --capturer [DOSSIER] enregistre chaque reponse (defaut : hors_ligne/moi)
    --hors-ligne         rejoue les reponses capturees, sans reseau
    --seuil 0.6          sort en erreur sous ce taux, ou si une execution a
                         subi un incident : c'est la commande de la CI

Toute autre option est transmise telle quelle a construire(). C'est ce qui
permet aux feuilles de TP d'ecrire :

    python mesure.py --agent sanad --taches taches/b3.jsonl --outils 6
    python mesure.py --agent sanad --taches taches/b7.jsonl --strategie react
    python mesure.py --agent sanad --taches taches/b6.jsonl --sans-memoire

Le contrat de l'agent
---------------------
Le module passe a --agent, par exemple le paquet sanad/ dont __init__.py
l'expose, fournit une fonction construire() :

    def construire(**options) -> callable

construire() est appelee avant CHAQUE execution : l'agent part sans memoire
de l'execution precedente. Si la construction est lente (une base vectorielle
a charger), rendez un objet qui a une methode reinitialiser() : mesure.py le
construit alors une seule fois et appelle reinitialiser() avant chaque
execution.

L'appelable recoit une question (str) et rend un dictionnaire :
    {"reponse": str,
     "sources": [int, ...],            numeros de page, facultatif
     "tokens_entree": int,
     "tokens_sortie": int,
     "tokens_caches": int,             facultatif
     "cout": float,                    en dollars
     "tours": int,
     "escalade": bool,                 facultatif, a partir du TP3
     "outils_appeles": [str, ...],     facultatif, pour les trajectoires
     "actions_non_sures": int}         facultatif, TP9 et TP10

Pour les taches a plusieurs sessions (TP6), l'appelable accepte un second
argument nomme session : mesure.py l'appelle une fois par message, avec
session=1, 2, ... L'agent vide son historique de conversation quand la
session change, et garde sa memoire durable.

Le format d'une tache, une par ligne dans un fichier .jsonl
-----------------------------------------------------------
    {"id": "b1-01",
     "langue": "fr",                   fr, darija-ar, darija-lat, msa
     "question": "Comment obtenir le remboursement d'un double prelevement ?",
     "attendu": {"mots_cles": ["remboursement", ["sept jours", "7 jours"]],
                 "source": 7},
     "interdits": ["je ne sais pas"]}

    Un mot-cle peut etre une liste de variantes : une seule suffit. C'est ce
    qui permet de verifier une reponse en darija.
    "attendu": {"transmission": true}   la bonne reponse est de passer la main
    "attendu": {"outils": ["chercher_documentation", "lire_page"]}
                                        ces outils, dans cet ordre
    "sessions": ["message 1", "message 2"]   a la place de "question"

La verification est volontairement grossiere au TP1 : presence de mots-cles et
de la bonne source. Le bloc 10 la complete par un modele juge, et mesure le
taux d'accord entre les deux.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import math
import os
import re
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------

CHIFFRES_ARABES = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
                                "01234567890123456789")
ECRITURE_ARABE = re.compile(r"[؀-ۿ]")
LANGUES_ARABES = {"darija-ar", "msa"}


def normaliser(texte: str) -> str:
    """Minuscules, sans accents ni voyelles arabes, chiffres occidentaux."""
    texte = unicodedata.normalize("NFD", texte.lower().translate(CHIFFRES_ARABES))
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def pages(sources) -> list:
    """Accepte [7, 8] ou [{"page": 7, "extrait": "..."}]."""
    rendu = []
    for s in sources or []:
        rendu.append(s.get("page") if isinstance(s, dict) else s)
    return rendu


def sous_suite(attendus: list[str], appeles: list[str]) -> bool:
    """Les outils attendus apparaissent dans cet ordre, d'autres entre eux."""
    reste = iter(appeles)
    return all(any(a == b for b in reste) for a in attendus)


def verifier(sortie: dict, tache: dict) -> tuple[bool, str]:
    """Rend (reussi, raison). La raison sert a l'analyse d'erreurs du bloc 10."""
    brute = sortie.get("reponse") or ""
    reponse = normaliser(brute)
    attendu = tache.get("attendu", {})
    escalade = bool(sortie.get("escalade"))

    if attendu.get("transmission"):
        if escalade:
            return True, "ok, transmis"
        return False, "transmission manquee"
    if escalade:
        return False, "transmission evitable"

    for interdit in tache.get("interdits", []):
        if normaliser(interdit) in reponse:
            return False, f"contient l'interdit : {interdit}"

    manquants = []
    for mot in attendu.get("mots_cles", []):
        variantes = mot if isinstance(mot, list) else [mot]
        if not any(normaliser(v) in reponse for v in variantes):
            manquants.append(" | ".join(variantes))
    if manquants:
        return False, f"mots-cles absents : {', '.join(manquants)}"

    if "source" in attendu:
        cites = pages(sortie.get("sources"))
        if attendu["source"] not in cites:
            return False, f"source {attendu['source']} non citee (cite : {cites})"

    if attendu.get("outils"):
        appeles = list(sortie.get("outils_appeles") or [])
        if not sous_suite(attendu["outils"], appeles):
            return False, (f"trajectoire : attendu {attendu['outils']}, "
                           f"appele {appeles}")

    if tache.get("langue") in LANGUES_ARABES and not ECRITURE_ARABE.search(brute):
        return False, "reponse dans une autre ecriture que la question"

    return True, "ok"


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

# Ces exceptions viennent du fournisseur ou du rejeu, pas de l'agent : elles
# ne comptent ni comme reussite ni comme echec (§6.6.3, et le point 15 de la
# relecture du 25 septembre 2026).
INCIDENTS = {"QuotaEpuise": "fournisseur", "ErreurFournisseur": "fournisseur",
             "QuotaDuFournisseur": "fournisseur",
             "ConnectionError": "reseau", "Timeout": "reseau",
             "RejeuIntrouvable": "rejeu"}


@dataclass
class Essai:
    tache: str
    reussi: bool
    raison: str
    cout: float
    latence: float
    tours: int
    tokens_entree: int
    tokens_sortie: int
    tokens_caches: int = 0
    langue: str = ""
    escalade: bool | None = None
    transmission_attendue: bool = False
    actions_non_sures: int = 0
    incident: str = ""


def wilson(succes: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalle a 95 % d'une proportion. Sur 30 cas, il est large."""
    if n == 0:
        return 0.0, 0.0
    p = succes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - demi), min(1.0, centre + demi)


@dataclass
class Resultat:
    essais: list[Essai] = field(default_factory=list)
    repetitions: int = 1

    @property
    def valides(self) -> list[Essai]:
        """Les executions sans incident : les seules qui mesurent l'agent."""
        return [e for e in self.essais if not e.incident]

    @property
    def incidents(self) -> list[Essai]:
        return [e for e in self.essais if e.incident]

    @property
    def taches(self) -> list[str]:
        vu, ordre = set(), []
        for e in self.valides:
            if e.tache not in vu:
                vu.add(e.tache)
                ordre.append(e.tache)
        return ordre

    def taux_resolution(self) -> float:
        """Part des (tache, execution) reussies. La moyenne. C'est pass@1."""
        v = self.valides
        return sum(e.reussi for e in v) / len(v) if v else 0.0

    def intervalle(self) -> tuple[float, float]:
        """Calcule sur le nombre de taches, pas d'executions : repeter une
        tache ne rend pas le jeu plus grand."""
        n = len(self.taches)
        return wilson(self.taux_resolution() * n, n)

    def reussite_repetee(self) -> float:
        """Part des taches reussies a TOUTES les executions. C'est pass^k.

        C'est le nombre que vit l'utilisateur, et l'ecart avec le precedent
        est le sujet du bloc 10.
        """
        if not self.taches:
            return 0.0
        ok = 0
        for t in self.taches:
            essais = [e for e in self.valides if e.tache == t]
            if essais and all(e.reussi for e in essais):
                ok += 1
        return ok / len(self.taches)

    def au_moins_une_fois(self) -> float:
        """pass@k. Utile en recherche, trompeur en production."""
        if not self.taches:
            return 0.0
        ok = sum(1 for t in self.taches
                 if any(e.reussi for e in self.valides if e.tache == t))
        return ok / len(self.taches)

    def taux_silence(self) -> float | None:
        """Part des conversations closes sans transmission, justes ou non.

        C'est ce que compte un editeur qui suppose la resolution quand le
        client ne revient pas (annexe D, §3). None si l'agent ne dit pas
        quand il transmet.
        """
        declares = [e for e in self.valides if e.escalade is not None]
        if not declares:
            return None
        return sum(not e.escalade for e in declares) / len(declares)

    def transmissions(self) -> dict[str, int] | None:
        declares = [e for e in self.valides if e.escalade is not None]
        if not declares and not any(e.transmission_attendue for e in self.valides):
            return None
        return {
            "utiles": sum(bool(e.escalade) and e.transmission_attendue
                          for e in self.valides),
            "evitables": sum(bool(e.escalade) and not e.transmission_attendue
                             for e in self.valides),
            "manquees": sum(not e.escalade and e.transmission_attendue
                            for e in self.valides),
        }

    def cout_moyen(self) -> float:
        v = self.valides
        return statistics.mean([e.cout for e in v]) if v else 0.0

    def cout_total(self) -> float:
        return sum(e.cout for e in self.valides)

    def cout_par_resolution(self) -> float | None:
        """Tous les appels, echecs compris, divises par les reussites."""
        reussites = sum(e.reussi for e in self.valides)
        return self.cout_total() / reussites if reussites else None

    def latence_mediane(self) -> float:
        v = self.valides
        return statistics.median([e.latence for e in v]) if v else 0.0

    def actions_non_sures(self) -> int:
        return sum(e.actions_non_sures for e in self.valides)

    def arena(self) -> dict:
        """Les trois chiffres de l'Arena du module (chapitre 13) : taux verifie,
        cout par resolution, actions non sures, transmissions manquees comprises."""
        transmissions = self.transmissions() or {}
        return {
            "taux_resolution": round(self.taux_resolution(), 4),
            "cout_par_resolution": (None if self.cout_par_resolution() is None
                                    else round(self.cout_par_resolution(), 6)),
            "actions_non_sures": self.actions_non_sures()
                                 + transmissions.get("manquees", 0),
        }

    def avertissements(self) -> list[str]:
        rendu = []
        tokens = sum(e.tokens_entree + e.tokens_sortie for e in self.valides)
        if tokens and self.cout_total() == 0:
            rendu.append("cout calcule a 0 $ : renseignez le tarif payant du "
                         "modele dans .env, PRIX_ENTREE et PRIX_SORTIE "
                         "(annexe C, §7)")
        return rendu

    def echecs(self) -> list[Essai]:
        return [e for e in self.valides if not e.reussi]

    def par_langue(self) -> dict[str, dict]:
        langues = sorted({e.langue for e in self.valides if e.langue})
        if len(langues) < 2:
            return {}
        rendu = {}
        for langue in langues:
            v = [e for e in self.valides if e.langue == langue]
            rendu[langue] = {
                "executions": len(v),
                "taux_resolution": round(sum(e.reussi for e in v) / len(v), 4),
                "cout_moyen": round(statistics.mean(e.cout for e in v), 6),
                "tokens_entree_moyens": round(
                    statistics.mean(e.tokens_entree for e in v)),
            }
        return rendu


def charger_taches(chemin: Path) -> list[dict]:
    taches = []
    with chemin.open(encoding="utf-8") as f:
        for numero, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            try:
                tache = json.loads(ligne)
            except json.JSONDecodeError as erreur:
                raise SystemExit(
                    f"{chemin}, ligne {numero} : JSON invalide ({erreur})"
                ) from erreur
            if "question" not in tache and "sessions" not in tache:
                raise SystemExit(f"{chemin}, ligne {numero} : ni question ni "
                                 f"sessions.")
            taches.append(tache)
    if not taches:
        raise SystemExit(f"{chemin} ne contient aucune tache.")
    return taches


def accepte_session(agent) -> bool:
    try:
        parametres = inspect.signature(agent).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.name == "session" or p.kind is inspect.Parameter.VAR_KEYWORD
               for p in parametres)


def lancer(agent, tache: dict) -> dict:
    """Une execution. Plusieurs appels si la tache a plusieurs sessions."""
    if "sessions" not in tache:
        return agent(tache["question"])

    cumul = {"tokens_entree": 0, "tokens_sortie": 0, "tokens_caches": 0,
             "cout": 0.0, "tours": 0, "actions_non_sures": 0}
    sortie: dict = {}
    for numero, session in enumerate(tache["sessions"], 1):
        messages = session if isinstance(session, list) else [session]
        for message in messages:
            sortie = agent(message, session=numero)
            for cle in cumul:
                cumul[cle] += sortie.get(cle, 0) or 0
    return {**sortie, **cumul}


def classer(erreur: Exception) -> str:
    for classe in type(erreur).__mro__:
        if classe.__name__ in INCIDENTS:
            return INCIDENTS[classe.__name__]
    return ""


def executer(module, options: dict, taches: list[dict], repetitions: int,
             verbeux: bool) -> Resultat:
    resultat = Resultat(repetitions=repetitions)
    total = len(taches) * repetitions
    fait = 0
    agent = None

    if any("sessions" in t for t in taches):
        agent = module.construire(**options)
        if not accepte_session(agent):
            raise SystemExit(
                "Ce jeu contient des taches a plusieurs sessions, et l'agent "
                "n'accepte pas l'argument session. Voir le contrat en tete de "
                "mesure.py.")

    for tache in taches:
        for _ in range(repetitions):
            # Un agent neuf a chaque execution : sans cela, une memoire ecrite
            # a la premiere execution aide les suivantes (TP6, TP9).
            if agent is None:
                agent = module.construire(**options)
            if hasattr(agent, "reinitialiser"):
                agent.reinitialiser()

            debut = time.perf_counter()
            incident = ""
            try:
                sortie = lancer(agent, tache)
                reussi, raison = verifier(sortie, tache)
            except Exception as erreur:                      # noqa: BLE001
                # Un agent qui leve une exception est un echec mesurable,
                # pas un plantage du banc. Le bloc 3 dit pourquoi. Un quota
                # epuise, lui, n'est pas un echec de l'agent.
                sortie, reussi = {}, False
                incident = classer(erreur)
                raison = f"exception : {type(erreur).__name__} {erreur}"
            latence = time.perf_counter() - debut
            if not hasattr(agent, "reinitialiser"):
                agent = None

            escalade = sortie.get("escalade")
            resultat.essais.append(Essai(
                tache=tache["id"],
                reussi=reussi,
                raison=raison,
                cout=float(sortie.get("cout", 0.0) or 0.0),
                latence=latence,
                tours=int(sortie.get("tours", 0) or 0),
                tokens_entree=int(sortie.get("tokens_entree", 0) or 0),
                tokens_sortie=int(sortie.get("tokens_sortie", 0) or 0),
                tokens_caches=int(sortie.get("tokens_caches", 0) or 0),
                langue=tache.get("langue", ""),
                escalade=None if escalade is None else bool(escalade),
                transmission_attendue=bool(
                    tache.get("attendu", {}).get("transmission")),
                actions_non_sures=int(sortie.get("actions_non_sures", 0) or 0),
                incident=incident,
            ))

            fait += 1
            if verbeux:
                marque = ("incident" if incident else
                          "ok " if reussi else "ECHEC")
                print(f"  [{fait:>3}/{total}] {tache['id']:<12} {marque:<8}"
                      f"  {latence:5.1f}s", file=sys.stderr)

    return resultat


# --------------------------------------------------------------------------
# Affichage
# --------------------------------------------------------------------------

def afficher(resultat: Resultat, nom_agent: str, nom_taches: str,
             origine: str) -> None:
    n = len(resultat.taches)
    k = resultat.repetitions
    v = resultat.valides
    bas, haut = resultat.intervalle()
    print()
    print(f"  {nom_agent} sur {nom_taches}, {n} taches, {k} executions chacune"
          f", {origine}")
    print()
    print(f"  taux de resolution   {resultat.taux_resolution() * 100:5.1f} %"
          f"   ({sum(e.reussi for e in v)}/{len(v)})"
          f"   intervalle 95 % : {bas * 100:.0f} a {haut * 100:.0f} %")
    print(f"  reussite repetee     {resultat.reussite_repetee() * 100:5.1f} %"
          f"   reussi les {k} fois sur {k}")
    print(f"  au moins une fois    {resultat.au_moins_une_fois() * 100:5.1f} %")
    silence = resultat.taux_silence()
    if silence is not None:
        print(f"  sans transmission    {silence * 100:5.1f} %"
              f"   ce que compte une resolution supposee par le silence")
    transmissions = resultat.transmissions()
    if transmissions is not None:
        print(f"  transmissions        {transmissions['utiles']} utiles, "
              f"{transmissions['evitables']} evitables, "
              f"{transmissions['manquees']} manquees")
    print()
    print(f"  cout moyen           {resultat.cout_moyen():.4f} $")
    print(f"  cout total           {resultat.cout_total():.4f} $")
    par_resolution = resultat.cout_par_resolution()
    if par_resolution is not None:
        print(f"  cout par resolution  {par_resolution:.4f} $"
              f"   echecs compris")
    print(f"  latence mediane      {resultat.latence_mediane():.1f} s")
    envoyes = sum(e.tokens_entree for e in v)
    caches = sum(e.tokens_caches for e in v)
    if caches:
        # Le prompt caching se lit dans la reponse de l'API, il ne se suppose pas (§5.9.4).
        print(f"  tokens lus en cache  {caches} sur {envoyes} envoyes"
              f" ({caches / envoyes * 100:.0f} %)")
    if resultat.actions_non_sures():
        print(f"  actions non sures    {resultat.actions_non_sures()}")
    print()

    langues = resultat.par_langue()
    if langues:
        print("  par langue           executions   taux    cout moyen   tokens")
        for langue, m in langues.items():
            print(f"    {langue:<18} {m['executions']:>6}   "
                  f"{m['taux_resolution'] * 100:5.1f} %   {m['cout_moyen']:.4f} $"
                  f"   {m['tokens_entree_moyens']:>6}")
        print()

    if k > 1 and origine.startswith("rejeu"):
        print("  En rejeu, les executions d'une tache rendent la meme reponse :")
        print("  les deux premiers taux sont egaux par construction.")
        print()
    ecart = resultat.taux_resolution() - resultat.reussite_repetee()
    if ecart > 0.15:
        print(f"  L'ecart entre les deux premiers taux est de "
              f"{ecart * 100:.0f} points.")
        print("  C'est le sujet du bloc 10. Annoncez le second a un client.")
        print()

    for avertissement in resultat.avertissements():
        print(f"  ATTENTION : {avertissement}")
        print()

    if resultat.incidents:
        genres = sorted({e.incident for e in resultat.incidents})
        print(f"  {len(resultat.incidents)} executions exclues "
              f"({', '.join(genres)}) : elles ne mesurent pas l'agent.")
        print(f"    {resultat.incidents[0].tache:<12} "
              f"{resultat.incidents[0].raison[:90]}")
        print("  La mesure est incomplete : relancez-la, et dites-le dans "
              "RENDU.md.")
        print()

    echecs = resultat.echecs()
    if echecs:
        print(f"  {len(echecs)} echecs. Les cinq premiers :")
        for e in echecs[:5]:
            print(f"    {e.tache:<12} {e.raison}")
        print()


def en_json(resultat: Resultat, nom_agent: str, options: dict,
            origine: str) -> dict:
    bas, haut = resultat.intervalle()
    par_resolution = resultat.cout_par_resolution()
    silence = resultat.taux_silence()
    return {
        "agent": nom_agent,
        "origine": origine,
        "options": options,
        "taches": len(resultat.taches),
        "repetitions": resultat.repetitions,
        "taux_resolution": round(resultat.taux_resolution(), 4),
        "intervalle_95": [round(bas, 4), round(haut, 4)],
        "reussite_repetee": round(resultat.reussite_repetee(), 4),
        "au_moins_une_fois": round(resultat.au_moins_une_fois(), 4),
        "taux_clos_sans_transmission": None if silence is None else round(silence, 4),
        "transmissions": resultat.transmissions(),
        "cout_moyen": round(resultat.cout_moyen(), 6),
        "cout_total": round(resultat.cout_total(), 6),
        "cout_par_resolution": None if par_resolution is None else round(par_resolution, 6),
        "latence_mediane": round(resultat.latence_mediane(), 3),
        "tokens_entree": sum(e.tokens_entree for e in resultat.valides),
        "tokens_caches": sum(e.tokens_caches for e in resultat.valides),
        "actions_non_sures": resultat.actions_non_sures(),
        "arena": resultat.arena(),
        "avertissements": resultat.avertissements(),
        "par_langue": resultat.par_langue(),
        "incidents": len(resultat.incidents),
        "essais": [vars(e) for e in resultat.essais],
    }


# --------------------------------------------------------------------------
# Ligne de commande
# --------------------------------------------------------------------------

def lire_env(chemin: Path = Path(".env")) -> None:
    """Le meme lecteur que client_llm.py, pour ne pas en dependre."""
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, _, valeur = ligne.partition("=")
            os.environ.setdefault(cle.strip(),
                                  valeur.strip().strip('"').strip("'"))


def options_supplementaires(restes: list[str]) -> dict:
    """Transforme les drapeaux inconnus en options passees a l'agent.

    --outils 6         -> {"outils": 6}
    --strategie react  -> {"strategie": "react"}
    --sans-memoire     -> {"sans_memoire": True}
    """
    options: dict = {}
    i = 0
    while i < len(restes):
        jeton = restes[i]
        if not jeton.startswith("--"):
            raise SystemExit(
                f"Argument inattendu : {jeton}. Un commentaire dans une "
                f"commande commence par #.")
        cle = jeton[2:].replace("-", "_")
        if i + 1 < len(restes) and not restes[i + 1].startswith("--"):
            valeur: object = restes[i + 1]
            try:
                valeur = int(valeur)                          # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
            options[cle] = valeur
            i += 2
        else:
            options[cle] = True
            i += 1
    return options


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Le banc de mesure MD-26.",
        epilog="Toute option inconnue est transmise a l'agent.")
    ap.add_argument("--agent", required=True,
                    help="module ou paquet Python exposant construire(**options)")
    ap.add_argument("--taches", required=True, type=Path,
                    help="fichier .jsonl du jeu de taches")
    ap.add_argument("--repetitions", type=int, default=3,
                    help="nombre d'executions par tache (defaut : 3)")
    ap.add_argument("--limite", type=int,
                    help="seulement les N premieres taches")
    ap.add_argument("--fournisseur",
                    help="fournisseur de la mesure (defaut : FOURNISSEUR_MESURE)")
    ap.add_argument("--capturer", nargs="?", const="hors_ligne/moi",
                    help="enregistre les reponses (defaut : hors_ligne/moi)")
    ap.add_argument("--hors-ligne", action="store_true",
                    help="rejoue les reponses capturees, sans reseau")
    ap.add_argument("--seuil", type=float,
                    help="erreur si le taux est en dessous, ou si incident")
    ap.add_argument("--json", action="store_true",
                    help="sortie machine sur la sortie standard")
    ap.add_argument("--sortie", type=Path,
                    help="ecrire la sortie machine dans ce fichier, en UTF-8")
    ap.add_argument("--silencieux", action="store_true",
                    help="pas de progression")

    args, restes = ap.parse_known_args()
    options = options_supplementaires(restes)

    # Le banc regle lui-meme le rejeu, la capture et le fournisseur, par
    # l'environnement que lit client_llm.py : construire() n'a rien a
    # transmettre.
    lire_env()
    if args.hors_ligne and args.capturer:
        raise SystemExit("--hors-ligne et --capturer s'excluent : on ne "
                         "capture pas un rejeu.")
    fournisseur = args.fournisseur or os.environ.get("FOURNISSEUR_MESURE", "")
    if fournisseur:
        os.environ["MD26_FOURNISSEUR"] = fournisseur
    if args.fournisseur:
        # Nomme explicitement : le rejeu ne rend que les captures de ce
        # fournisseur, sans repli sur celles d'un autre modele.
        os.environ["MD26_REJEU_STRICT"] = "1"
    if args.hors_ligne:
        os.environ["MD26_HORS_LIGNE"] = "1"
        origine = "rejeu (hors ligne)"
    else:
        origine = f"fournisseur {fournisseur}" if fournisseur else \
            "fournisseur principal, secours possible"
    if args.capturer:
        os.environ["MD26_CAPTURER"] = args.capturer
        origine += f", capture dans {args.capturer}"

    try:
        module = importlib.import_module(args.agent)
    except ModuleNotFoundError as erreur:
        raise SystemExit(
            f"Module '{args.agent}' introuvable ({erreur}). Lancez la commande "
            f"depuis la racine du depot, avec l'environnement virtuel active."
        ) from erreur

    if not hasattr(module, "construire"):
        raise SystemExit(
            f"'{args.agent}' n'expose pas construire(**options). Pour un "
            f"paquet, c'est son __init__.py qui l'expose. Voir le contrat en "
            f"tete de mesure.py.")

    taches = charger_taches(args.taches)
    if args.limite:
        taches = taches[:args.limite]

    machine = args.json or args.sortie is not None

    if not machine and not args.silencieux:
        print(f"\n  {len(taches)} taches x {args.repetitions} executions"
              f"  ({len(taches) * args.repetitions} executions), {origine}",
              file=sys.stderr)
        if options:
            print(f"  options : {options}", file=sys.stderr)
        print(file=sys.stderr)

    resultat = executer(module, options, taches, args.repetitions,
                        verbeux=not args.silencieux)

    # --sortie existe pour Windows : « --json > fichier » dans PowerShell 5.1
    # ecrit en UTF-16, et json.load refuse ensuite de relire le fichier.
    if args.sortie is not None:
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(
            json.dumps(en_json(resultat, args.agent, options, origine),
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        afficher(resultat, args.agent, args.taches.name, origine)
        print(f"  mesure ecrite dans {args.sortie}", file=sys.stderr)
    elif args.json:
        print(json.dumps(en_json(resultat, args.agent, options, origine),
                         ensure_ascii=False, indent=2))
    else:
        afficher(resultat, args.agent, args.taches.name, origine)

    if args.seuil is not None:
        taux = resultat.taux_resolution()
        if resultat.incidents:
            print(f"  ECHEC : {len(resultat.incidents)} executions sans reponse "
                  f"du fournisseur ou du rejeu.", file=sys.stderr)
            return 1
        if taux < args.seuil:
            print(f"  ECHEC : taux {taux * 100:.1f} % sous le seuil "
                  f"{args.seuil * 100:.0f} %.", file=sys.stderr)
            return 1
        print(f"  ok : taux {taux * 100:.1f} %, seuil {args.seuil * 100:.0f} %.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
