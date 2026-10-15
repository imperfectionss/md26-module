#!/bin/sh
# MD-26 : installer votre poste macOS ou Linux, en une commande.
#
# Lisez ce script avant de le lancer, comme tout script venu d'ailleurs. Il
# fait cinq choses, dans l'ordre, et s'arrete a la premiere qui echoue :
#
#   1. verifie Python 3.10 ou plus, et git
#   2. clone votre copie du depot dans ~/md26
#   3. cree l'environnement virtuel et installe ses bibliotheques
#   4. cree votre fichier .env
#   5. lance python verifier.py
#
# Lancement :   sh installer_md26.sh
# ou, avec l'adresse de votre copie :   sh installer_md26.sh https://github.com/...

HOTE_MIROIR="192.168.137.1"
MIROIR="http://$HOTE_MIROIR:8000"
MODULE="https://github.com/imperfectionss/md26-module.git"
DOSSIER="$HOME/md26"
DEPOT="$1"

etape() { printf '\n== %s\n' "$1"; }
ok() { printf '   ok  %s\n' "$1"; }
arret() { printf '\n   ECHEC  %s\n' "$1"; exit 1; }

EN_SALLE=0
if curl -s -m 3 -o /dev/null "$MIROIR/manifeste.json"; then EN_SALLE=1; fi

etape "1/5  Python et git"
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  if [ "$(uname)" = "Darwin" ]; then
    printf '   Python 3.10 ou plus est absent. Installez-le, puis relancez :\n'
    if [ "$EN_SALLE" = 1 ]; then
      printf '   curl -O %s/installeurs/macos/python-3.13.15-macos11.pkg\n' "$MIROIR"
      printf '   sudo installer -pkg python-3.13.15-macos11.pkg -target /\n'
    else
      printf '   https://www.python.org/downloads/macos/\n'
    fi
  else
    printf '   Python 3.10 ou plus est absent : sudo apt install python3 python3-venv\n'
  fi
  exit 1
fi
ok "$($PY --version)"
command -v git >/dev/null 2>&1 || arret "git est absent. macOS : tapez git une fois, l'installation se propose. Linux : sudo apt install git."
ok "$(git --version)"

etape "2/5  Votre copie du depot"
if [ -d "$DOSSIER/.git" ]; then
  ok "le dossier $DOSSIER existe deja, on le garde"
else
  if [ -z "$DEPOT" ]; then
    printf '   L adresse de la copie privee de votre binome, sur GitHub : '
    read -r DEPOT
  fi
  [ -n "$DEPOT" ] || arret "Il faut l'adresse de votre copie (polycopie, partie R3)."
  git clone "$DEPOT" "$DOSSIER" || arret "La copie n'a pas pu etre clonee. Verifiez l'adresse et vos droits."
  git -C "$DOSSIER" remote add module "$MODULE"
  ok "depot clone dans $DOSSIER"
fi
cd "$DOSSIER" || exit 1

etape "3/5  L'environnement virtuel"
[ -x .venv/bin/python ] || "$PY" -m venv .venv || arret "venv a echoue. Linux : sudo apt install python3-venv."
if [ "$EN_SALLE" = 1 ] && .venv/bin/python -m pip install -q --no-index --trusted-host "$HOTE_MIROIR" \
     --find-links="$MIROIR/roue/" -r requirements.txt; then
  ok "bibliotheques installees depuis le miroir"
else
  .venv/bin/python -m pip install -q -r requirements.txt || arret "Les bibliotheques ne se sont pas installees."
  ok "bibliotheques installees"
fi

etape "4/5  Votre fichier .env"
[ -f .env ] || cp .env.exemple .env
[ "$(git check-ignore .env)" = ".env" ] || arret ".env n'est pas ignore par git. Appelez l'enseignant avant tout commit."
ok ".env pret : ouvrez-le et remplacez chaque ... par votre cle"

etape "5/5  python verifier.py"
.venv/bin/python verifier.py
printf '\nTermine. Votre dossier : %s\n' "$DOSSIER"
