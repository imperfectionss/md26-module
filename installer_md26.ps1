# MD-26 : installer votre poste Windows, en une commande.
#
# Lisez ce script avant de le lancer. C'est la regle du module pour tout
# script venu d'ailleurs, et celui-ci est court. Il fait six choses, dans
# l'ordre, et il s'arrete a la premiere qui echoue en disant pourquoi :
#
#   1. Python 3.13, s'il n'y a pas deja un Python 3.10 ou plus
#   2. git, s'il n'est pas deja la
#   3. votre copie du depot, dans le dossier md26 de votre repertoire
#   4. l'environnement virtuel, et ses bibliotheques
#   5. votre fichier .env, ouvert dans le Bloc-notes
#   6. python verifier.py
#
# Rien ne demande de droits administrateur. En salle, tout vient du miroir de
# l'enseignant ; chez vous, d'internet.
#
# Lancement, dans PowerShell :
#   powershell -ExecutionPolicy Bypass -File installer_md26.ps1

param(
    [string]$Depot = "",
    [string]$Miroir = "http://192.168.137.1:8000",
    [string]$Module = "https://github.com/imperfectionss/md26-module.git",
    [string]$Dossier = (Join-Path $HOME "md26"),
    [switch]$SansBlocNotes
)

# Pas "Stop" : sous Windows PowerShell 5.1, git et pip ecrivent leur
# progression sur la sortie d'erreur, et "Stop" en ferait des erreurs. Chaque
# etape verifie donc son resultat elle-meme.
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$PythonVersion = "3.13.15"

function Etape($texte) { Write-Host ""; Write-Host "== $texte" -ForegroundColor Cyan }
function Ok($texte) { Write-Host "   ok  $texte" -ForegroundColor Green }
function Arret($texte) { Write-Host ""; Write-Host "   ECHEC  $texte" -ForegroundColor Red; exit 1 }
function Rafraichir {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "Machine")
}

# Le miroir de la salle repond-il ? Sinon, on prend tout sur internet.
$EnSalle = $false
try {
    Invoke-WebRequest "$Miroir/manifeste.json" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null
    $EnSalle = $true
} catch { }
if ($EnSalle) { Write-Host "Miroir de la salle : $Miroir" } else { Write-Host "Pas de miroir : internet." }

function Prendre($chemin_miroir, $url_internet, $fichier) {
    $dest = Join-Path $env:TEMP $fichier
    if ($EnSalle) { $source = "$Miroir/$chemin_miroir" } else { $source = $url_internet }
    Write-Host "   telechargement de $fichier"
    try { Invoke-WebRequest $source -OutFile $dest -UseBasicParsing -ErrorAction Stop }
    catch { Arret "Telechargement impossible : $source" }
    return $dest
}

# ---------------------------------------------------------------- 1. Python
Etape "1/6  Python"
$Python = $null
foreach ($essai in @("3.14", "3.13", "3.12", "3.11", "3.10")) {
    try {
        $p = & py "-$essai" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $p) { $Python = $p.Trim(); break }
    } catch { }
}
if (-not $Python) {
    $cand = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
    if (Test-Path $cand) { $Python = $cand }
}
if (-not $Python) {
    $f = Prendre "installeurs/windows/python-$PythonVersion-amd64.exe" `
        "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" `
        "python-$PythonVersion-amd64.exe"
    Write-Host "   installation, une minute environ"
    Start-Process $f -Wait -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0"
    Rafraichir
    $Python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
    if (-not (Test-Path $Python)) { Arret "Python ne s'est pas installe. Appelez l'enseignant." }
}
Ok (& $Python --version)

# ------------------------------------------------------------------- 2. git
Etape "2/6  git"
Rafraichir
$Git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $Git) {
    $cand = Join-Path $env:LOCALAPPDATA "Programs\Git\cmd\git.exe"
    if (Test-Path $cand) { $Git = $cand }
}
if (-not $Git) {
    if ($EnSalle) {
        $f = Prendre "installeurs/windows/Git-64-bit.exe" "" "Git-64-bit.exe"
    } else {
        try { $rel = Invoke-RestMethod "https://api.github.com/repos/git-for-windows/git/releases/latest" -ErrorAction Stop }
        catch { Arret "GitHub ne repond pas : installez git depuis git-scm.com." }
        $a = $rel.assets | Where-Object { $_.name -match '^Git-.*-64-bit\.exe$' } | Select-Object -First 1
        $f = Prendre "" $a.browser_download_url "Git-64-bit.exe"
    }
    Write-Host "   installation, une minute environ"
    Start-Process $f -Wait -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL /SP- /SUPPRESSMSGBOXES"
    Rafraichir
    $Git = (Get-Command git -ErrorAction SilentlyContinue).Source
    if (-not $Git) { $Git = Join-Path $env:LOCALAPPDATA "Programs\Git\cmd\git.exe" }
    if (-not (Test-Path $Git)) { Arret "git ne s'est pas installe. Appelez l'enseignant." }
}
Ok (& $Git --version)

# ------------------------------------------------------- 3. la copie du depot
Etape "3/6  Votre copie du depot"
if (Test-Path (Join-Path $Dossier ".git")) {
    Ok "le dossier $Dossier existe deja, on le garde"
} else {
    if (-not $Depot) {
        Write-Host "   L'adresse de la copie privee de votre binome, sur GitHub."
        Write-Host "   Exemple : https://github.com/votre-compte/md26-binome-07"
        $Depot = Read-Host "   Adresse"
    }
    if (-not $Depot) { Arret "Il faut l'adresse de votre copie (polycopie, partie R3)." }
    Write-Host "   git clone : une fenetre de connexion a GitHub peut s'ouvrir, acceptez-la."
    & $Git clone $Depot $Dossier
    if ($LASTEXITCODE -ne 0) { Arret "La copie n'a pas pu etre clonee. Verifiez l'adresse, et que vous y avez acces." }
    Push-Location $Dossier
    & $Git remote add module $Module
    Pop-Location
    Ok "depot clone dans $Dossier, depot du module declare sous le nom module"
}
Set-Location $Dossier

# ------------------------------------------- 4. l'environnement virtuel
Etape "4/6  L'environnement virtuel"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $Python -m venv .venv }
$VPy = Join-Path $Dossier ".venv\Scripts\python.exe"
$fait = $false
if ($EnSalle) {
    $HoteMiroir = ([uri]$Miroir).Host
    & $VPy -m pip install -q --no-index --trusted-host $HoteMiroir --find-links="$Miroir/roue/" -r requirements.txt
    $fait = ($LASTEXITCODE -eq 0)
}
if (-not $fait) { & $VPy -m pip install -q -r requirements.txt; $fait = ($LASTEXITCODE -eq 0) }
if (-not $fait) { Arret "Les bibliotheques ne se sont pas installees." }
# PowerShell refuse sinon d'activer l'environnement virtuel (partie R3).
$politique = Get-ExecutionPolicy -Scope CurrentUser
if ($politique -eq "Undefined" -or $politique -eq "Restricted") {
    # Ce script tourne lui-meme en mode Bypass : PowerShell previent alors que
    # le reglage ne vaut qu'apres. L'avertissement n'est pas une erreur.
    try { Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction Stop }
    catch { }
}
Ok "environnement pret : .venv\Scripts\activate pour l'activer"

# ------------------------------------------------------------------ 5. .env
Etape "5/6  Votre fichier .env"
if (-not (Test-Path ".env")) { Copy-Item ".env.exemple" ".env"; Ok ".env cree depuis .env.exemple" }
else { Ok ".env existe deja, on n'y touche pas" }
$ignore = & $Git check-ignore .env
if ($ignore -ne ".env") { Arret ".env n'est pas ignore par git. Appelez l'enseignant avant tout commit." }
Write-Host "   Le Bloc-notes s'ouvre : remplacez chaque ... par votre cle, enregistrez, fermez."
if (-not $SansBlocNotes) { Start-Process notepad.exe ".env" -Wait }

# ------------------------------------------------------------ 6. la verification
Etape "6/6  python verifier.py"
& $VPy verifier.py
Write-Host ""
Write-Host "Termine. Un ECHEC ci-dessus se corrige avant le TP : le remede est ecrit dessous."
Write-Host "Votre dossier : $Dossier"
