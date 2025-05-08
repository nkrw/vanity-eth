import os
import sys
import argparse
import time
import re
import threading
import queue
from web3 import Web3
from eth_account import Account
import secrets
from datetime import datetime

# Configuration globale
NUM_THREADS = os.cpu_count()
DEFAULT_DEVICE = "CPU"  # CPU par défaut, possibilité d'ajouter GPU plus tard
RESULT_QUEUE = queue.Queue()
STOP_EVENT = threading.Event()
TOTAL_COUNTS = [0] * NUM_THREADS
FOUND_ADDRESSES = []
STATS_LOCK = threading.Lock()

# Liste des motifs notables
NOTABLE_PATTERNS = [
    '1337', '420', '69', 'dead', 'beef', 'cafe', 'babe', 'face', 'f00d',
    'abcd', '1234', 'bad', 'dad', 'ace', 'bed', 'cab', 'deed', 'fade'
]

# Classe pour les couleurs ANSI dans le terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_line():
    """Effacer la ligne courante dans le terminal"""
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()

def generate_keypair():
    """Génère une nouvelle paire de clés Ethereum"""
    priv = secrets.token_hex(32)
    private_key = "0x" + priv
    account = Account.from_key(private_key)
    return account

def check_match(address, prefix, suffix, regex_obj):
    """Vérifie si une adresse correspond aux critères spécifiés"""
    address_lower = address.lower()
    
    # Vérification du préfixe (après 0x)
    if prefix and not address_lower.startswith("0x" + prefix):
        return False
    
    # Vérification du suffixe
    if suffix and not address_lower.endswith(suffix):
        return False
    
    # Vérification regex
    if regex_obj and not regex_obj.search(address_lower[2:]):
        return False
    
    return True

def calculate_score(address, args):
    """Calcule un score pour l'adresse en fonction des critères spéciaux"""
    addr_hexpart = address.lower()[2:]  # Adresse sans le '0x'
    score = 0
    
    # Score de base pour correspondance prefix/suffix/regex
    if args.prefix:
        score += len(args.prefix) * 2
    if args.suffix:
        score += len(args.suffix) * 2
    if args.regex:
        score += 1
    
    # Mode zeros - compte le nombre de zéros
    if args.zeros:
        zero_count = addr_hexpart.count('0')
        score += zero_count * 3
    
    # Mode leading - caractère répété au début
    if args.leading:
        leading_char = args.leading.lower()
        # Compte combien de fois le caractère se répète au début
        leading_count = 0
        for char in addr_hexpart:
            if char == leading_char:
                leading_count += 1
            else:
                break
        score += leading_count * 4
    
    # Mode mirror - motifs en miroir
    if args.mirror:
        # Recherche de séquences en miroir (au moins 4 caractères)
        for i in range(len(addr_hexpart) - 3):
            for length in range(2, min(len(addr_hexpart) - i, 10) + 1):
                substr = addr_hexpart[i:i+length]
                reversed_substr = substr[::-1]
                
                # Vérifie si le motif inversé se trouve ailleurs dans l'adresse
                if reversed_substr in addr_hexpart and reversed_substr != substr:
                    score += length * 2
    
    # Mode notable - motifs remarquables
    if args.notable:
        for pattern in NOTABLE_PATTERNS:
            if pattern in addr_hexpart:
                score += len(pattern) * 2
    
    # Mode repeating - motif répété
    if args.repeating:
        pattern = args.repeating.lower()
        pattern_count = 0
        
        # Cherche le motif et compte ses occurrences
        i = 0
        while i <= len(addr_hexpart) - len(pattern):
            if addr_hexpart[i:i+len(pattern)] == pattern:
                pattern_count += 1
                i += len(pattern)
            else:
                i += 1
                
        if pattern_count > 1:
            score += pattern_count * len(pattern) * 2
    
    return score

def check_eth_balance(address, provider_url="https://rpc.ankr.com/eth"):
    """Vérifie le solde ETH d'une adresse"""
    try:
        web3 = Web3(Web3.HTTPProvider(provider_url))
        if web3.is_connected():
            balance_wei = web3.eth.get_balance(address)
            balance_eth = web3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        return 0
    except Exception as e:
        print(f"{Colors.YELLOW}Erreur lors de la vérification du solde: {str(e)}{Colors.ENDC}")
        return 0

def save_wallet(address, private_key, output_dir, file_format="txt", check_balance=False):
    """Enregistre les informations du portefeuille dans des fichiers"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Vérification du solde si demandé
    balance = None
    if check_balance:
        balance = check_eth_balance(address)
    
    # Format txt
    if file_format in ["txt", "all"]:
        # Ajout au fichier global
        with open(f"{output_dir}/wallets.txt", "a") as f:
            line = f"{address},{private_key}"
            if balance is not None:
                line += f",{balance}"
            f.write(line + "\n")
        
        # Fichier individuel
        with open(f"{output_dir}/wallet_{address[2:10]}_{timestamp}.txt", "w") as f:
            f.write(f"Address: {address}\n")
            f.write(f"Private Key: {private_key}\n")
            if balance is not None:
                f.write(f"Balance: {balance} ETH\n")
    
    # Format JSON
    if file_format in ["json", "all"]:
        import json
        data = {
            "address": address,
            "private_key": private_key,
            "created": timestamp
        }
        if balance is not None:
            data["balance"] = str(balance)
        
        with open(f"{output_dir}/wallet_{address[2:10]}_{timestamp}.json", "w") as f:
            json.dump(data, f, indent=2)
    
    return balance

def worker_thread(thread_id, args):
    """Fonction exécutée par chaque thread de travail"""
    regex_obj = re.compile(args.regex) if args.regex else None
    count = 0
    
    while not STOP_EVENT.is_set():
        # Génération d'une nouvelle paire de clés
        account = generate_keypair()
        address = account.address
        private_key = account.key.hex()
        
        # Vérification de la correspondance de base
        if check_match(address, args.prefix, args.suffix, regex_obj):
            # Calcul du score selon les critères spéciaux
            score = calculate_score(address, args)
            
            # Vérification du solde si demandé
            balance = None
            if args.check_balance:
                balance = check_eth_balance(address)
                
            # Ajout à la file des résultats
            RESULT_QUEUE.put((address, private_key, score, thread_id, balance))
        
        # Mise à jour des compteurs
        count += 1
        TOTAL_COUNTS[thread_id] = count

def display_header(args):
    """Affiche l'en-tête de l'application"""
    print(f"{Colors.BOLD}{Colors.BLUE}ETH VANITY ADDRESS GENERATOR{Colors.ENDC}")
    print(f"{Colors.BOLD}Configuration:{Colors.ENDC}")
    
    if args.prefix:
        print(f"  Prefix: {Colors.YELLOW}0x{args.prefix}{Colors.ENDC}")
    if args.suffix:
        print(f"  Suffix: {Colors.YELLOW}{args.suffix}{Colors.ENDC}")
    if args.regex:
        print(f"  Regex:  {Colors.YELLOW}{args.regex}{Colors.ENDC}")
    
    # Affichage des modes spéciaux
    special_modes = []
    if args.zeros:
        special_modes.append(f"{Colors.CYAN}zeros{Colors.ENDC}")
    if args.leading:
        special_modes.append(f"{Colors.CYAN}leading({args.leading}){Colors.ENDC}")
    if args.mirror:
        special_modes.append(f"{Colors.CYAN}mirror{Colors.ENDC}")
    if args.notable:
        special_modes.append(f"{Colors.CYAN}notable{Colors.ENDC}")
    if args.repeating:
        special_modes.append(f"{Colors.CYAN}repeating({args.repeating}){Colors.ENDC}")
    
    if special_modes:
        print(f"  Modes spéciaux: {', '.join(special_modes)}")
    
    print(f"  Device: {Colors.CYAN}{DEFAULT_DEVICE}{Colors.ENDC}, {args.threads} threads")
    
    if args.check_balance:
        print(f"  {Colors.GREEN}Mode check-balance activé{Colors.ENDC}")
    
    print("-" * 50)

def calculate_device_speed():
    """Calcule la vitesse par dispositif (CPU/thread)"""
    total = sum(TOTAL_COUNTS)
    speeds = []
    for i in range(NUM_THREADS):
        speeds.append((f"{DEFAULT_DEVICE}{i}", TOTAL_COUNTS[i]))
    return total, speeds

def main():
    global NUM_THREADS
    
    # Configuration du parser d'arguments
    parser = argparse.ArgumentParser(
        description='Générateur d\'adresses Ethereum avec préfixe/suffixe/regex personnalisés')
    
    # Options de base
    parser.add_argument('-p', '--prefix', type=str, default='', 
                      help='préfixe de l\'adresse (après 0x)')
    parser.add_argument('-s', '--suffix', type=str, default='', 
                      help='suffixe de l\'adresse')
    parser.add_argument('-r', '--regex', type=str, default='', 
                      help='motif regex pour filtrer les adresses')
    
    # Options de configuration
    parser.add_argument('-t', '--threads', type=int, default=NUM_THREADS,
                      help=f'nombre de threads (défaut: {NUM_THREADS})')
    parser.add_argument('-o', '--output', type=str, default='eth_wallets',
                      help='dossier de sortie (défaut: eth_wallets)')
    parser.add_argument('-f', '--format', type=str, choices=['txt', 'json', 'all'], 
                      default='txt', help='format de sortie (défaut: txt)')
    parser.add_argument('-c', '--check-balance', action='store_true',
                      help='vérifier le solde des adresses générées')
    parser.add_argument('-m', '--multiple', action='store_true',
                      help='continuer à chercher après avoir trouvé une adresse correspondante')
    
    # Modes spéciaux
    parser.add_argument('--zeros', action='store_true',
                      help='score les adresses contenant le plus de zéros')
    parser.add_argument('--leading', type=str, metavar='hex',
                      help='score les adresses commençant par le caractère hex donné')
    parser.add_argument('--mirror', action='store_true',
                      help='score les adresses avec motif en miroir')
    parser.add_argument('--notable', action='store_true',
                      help='score les adresses avec des motifs remarquables (1337, 420, etc.)')
    parser.add_argument('--repeating', type=str, metavar='hex',
                      help='score les adresses avec répétition du motif hex donné')
    
    args = parser.parse_args()
    
    # Validation des paramètres
    criterias_present = any([args.prefix, args.suffix, args.regex, 
                            args.zeros, args.leading, args.mirror, 
                            args.notable, args.repeating])
    
    if not criterias_present:
        print(f"{Colors.RED}Erreur: Spécifiez au moins un critère de recherche{Colors.ENDC}")
        sys.exit(1)
    
    # Vérification hexadécimale pour les options principales
    try:
        if args.prefix:
            int(args.prefix, 16)
        if args.suffix:
            int(args.suffix, 16)
        if args.leading:
            if len(args.leading) != 1 or not re.match(r'^[0-9a-fA-F]$', args.leading):
                raise ValueError("Le caractère leading doit être un seul caractère hexadécimal")
        if args.repeating:
            int(args.repeating, 16)
    except ValueError as e:
        print(f"{Colors.RED}Erreur: {str(e)}{Colors.ENDC}")
        sys.exit(1)
    
    # Vérification regex
    if args.regex:
        try:
            re.compile(args.regex)
        except re.error:
            print(f"{Colors.RED}Erreur: Expression régulière invalide{Colors.ENDC}")
            sys.exit(1)
    
    # Mise à jour du nombre de threads
    NUM_THREADS = args.threads
    global TOTAL_COUNTS
    TOTAL_COUNTS = [0] * NUM_THREADS
    
    # Affichage de l'en-tête
    display_header(args)
    
    # Initialisation des compteurs et du temps
    start_time = time.time()
    last_update = start_time
    
    # Démarrage des threads
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=worker_thread, args=(i, args))
        t.daemon = True
        threads.append(t)
        t.start()
    
    # Boucle principale
    try:
        while True:
            # Vérifier les nouveaux résultats
            try:
                while not RESULT_QUEUE.empty():
                    # Récupérer les résultats de la file
                    address, private_key, score, thread_id, balance = RESULT_QUEUE.get(block=False)
                    
                    # Effacer la ligne de stats
                    clear_line()
                    
                    # Afficher le résultat trouvé
                    elapsed = time.time() - start_time
                    total_addresses = sum(TOTAL_COUNTS)
                    
                    print(f"\n{Colors.GREEN}Adresse trouvée!{Colors.ENDC} Généré {Colors.YELLOW}{total_addresses:,}{Colors.ENDC} adresses")
                    print(f"  Address: {Colors.GREEN}{address}{Colors.ENDC}")
                    print(f"  Private key: {Colors.YELLOW}{private_key}{Colors.ENDC}")
                    print(f"  Score: {Colors.CYAN}{score}{Colors.ENDC}")
                    
                    # Afficher la balance si elle est disponible
                    if balance is not None:
                        if balance > 0:
                            print(f"  Balance: {Colors.RED}{balance} ETH{Colors.ENDC}")
                        else:
                            print(f"  Balance: {balance} ETH")
                    
                    # Sauvegarder le portefeuille
                    # Pas besoin de revérifier la balance si on l'a déjà
                    if balance is not None:
                        save_wallet(address, private_key, args.output, args.format, False)
                    else:
                        balance = save_wallet(address, private_key, args.output, args.format, args.check_balance)
                        if balance is not None and balance > 0:
                            print(f"  Balance: {Colors.RED}{balance} ETH{Colors.ENDC}")
                    
                    # Ajouter à la liste des adresses trouvées
                    FOUND_ADDRESSES.append(address)
                    
                    # Arrêter si on ne veut pas continuer en mode multiple
                    if not args.multiple:
                        STOP_EVENT.set()
                        break
                    
                    print("-" * 50)
                    
            except queue.Empty:
                pass
            
            # Mise à jour des statistiques toutes les 0.5 secondes
            current_time = time.time()
            if current_time - last_update >= 0.5:
                total_count = sum(TOTAL_COUNTS)
                
                # Affichage du compteur d'adresses générées
                clear_line()
                sys.stdout.write(f"\rRecherche d'adresses, générés: {Colors.YELLOW}{total_count:,}{Colors.ENDC}")
                sys.stdout.flush()
                
                last_update = current_time
            
            # Vérifier si on doit arrêter
            if STOP_EVENT.is_set():
                break
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interruption utilisateur. Arrêt en cours...{Colors.ENDC}")
    finally:
        # Arrêt des threads
        STOP_EVENT.set()
        for t in threads:
            t.join(0.5)
        
        # Statistiques finales
        total_elapsed = time.time() - start_time
        total_generated = sum(TOTAL_COUNTS)
        
        print(f"\n{Colors.BOLD}Statistiques finales:{Colors.ENDC}")
        print(f"  Temps total: {int(total_elapsed // 60):02d}:{int(total_elapsed % 60):02d}")
        print(f"  Adresses générées: {total_generated:,}")
        print(f"  Vitesse moyenne: {total_generated / total_elapsed:.2f} addr/s")
        found_count = len(FOUND_ADDRESSES)
        if found_count > 0:
            print(f"  Adresses trouvées: {found_count}")
        print(f"  Adresses stockées dans: {args.output}/")

if __name__ == "__main__":
    main()