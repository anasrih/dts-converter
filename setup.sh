#!/bin/bash

# Définir des couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERREUR]${NC} $1"
}

# Vérifier si python3 est installé
if ! command -v python3 &> /dev/null; then
    print_error "Python3 n'est pas installé. Veuillez l'installer avant de continuer."
    exit 1
fi

# Vérifier si pip est installé
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 n'est pas installé. Veuillez l'installer avant de continuer."
    exit 1
fi

# Vérifier si venv est installé
python3 -m venv --help &> /dev/null
if [ $? -ne 0 ]; then
    print_warning "Le module venv n'est pas disponible. Tentative d'installation..."
    pip3 install virtualenv
    if [ $? -ne 0 ]; then
        print_error "Impossible d'installer virtualenv. Veuillez l'installer manuellement."
        exit 1
    fi
    VENV_CMD="virtualenv"
else
    VENV_CMD="python3 -m venv"
fi

# Vérifier si ffmpeg est installé
if ! command -v ffmpeg &> /dev/null; then
    print_warning "ffmpeg n'est pas installé. Il est requis pour le fonctionnement de l'API."
    
    # Détection du système d'exploitation pour recommander l'installation de ffmpeg
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            print_message "Sous Debian/Ubuntu, vous pouvez installer ffmpeg avec:"
            echo "sudo apt-get update && sudo apt-get install -y ffmpeg"
        elif command -v dnf &> /dev/null; then
            print_message "Sous Fedora, vous pouvez installer ffmpeg avec:"
            echo "sudo dnf install ffmpeg"
        elif command -v yum &> /dev/null; then
            print_message "Sous CentOS/RHEL, vous pouvez installer ffmpeg avec:"
            echo "sudo yum install ffmpeg"
        elif command -v pacman &> /dev/null; then
            print_message "Sous Arch Linux, vous pouvez installer ffmpeg avec:"
            echo "sudo pacman -S ffmpeg"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_message "Sous macOS, vous pouvez installer ffmpeg avec:"
        echo "brew install ffmpeg"
    fi
    
    read -p "Voulez-vous continuer sans ffmpeg? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Installation annulée. Veuillez installer ffmpeg et réessayer."
        exit 1
    fi
fi

# Créer l'environnement virtuel
print_message "Création de l'environnement virtuel..."
$VENV_CMD venv
if [ $? -ne 0 ]; then
    print_error "Erreur lors de la création de l'environnement virtuel."
    exit 1
fi

# Activer l'environnement virtuel
print_message "Activation de l'environnement virtuel..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    print_error "Erreur lors de l'activation de l'environnement virtuel."
    exit 1
fi

# Installer les dépendances
print_message "Installation des dépendances..."
pip install fastapi uvicorn pydantic requests
if [ $? -ne 0 ]; then
    print_error "Erreur lors de l'installation des dépendances."
    exit 1
fi

# Créer un script de démarrage
cat > start_api.sh <<EOF
#!/bin/bash
source venv/bin/activate
uvicorn dts_to_eac3:app --reload --host 0.0.0.0 --port 8000
EOF
chmod +x start_api.sh

# Afficher les instructions
print_message "Installation terminée avec succès!"
print_message "Pour démarrer l'API, exécutez: ./start_api.sh"
print_message "L'API sera accessible à l'adresse: http://localhost:8000"
print_message "Documentation de l'API: http://localhost:8000/docs"

# Désactiver l'environnement virtuel
deactivate