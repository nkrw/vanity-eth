# ETH VANITY ADDRESS GENERATOR

## Description
Ce programme génère des adresses Ethereum "vanity" (personnalisées) selon différents critères définis par l'utilisateur. Il permet de chercher des adresses avec des préfixes, suffixes ou motifs spécifiques.

## Usage
```
python eth_vanity.py [OPTIONS]
```

## Options

### Options de base
```
-p, --prefix <hex>          Spécifie un préfixe hexadécimal pour l'adresse (après 0x).
-s, --suffix <hex>          Spécifie un suffixe hexadécimal pour l'adresse.
-r, --regex <pattern>       Définit un motif regex pour filtrer les adresses.
-m, --multiple              Continue la recherche après avoir trouvé une adresse.
```

### Options de configuration
```
-t, --threads <number>      Définit le nombre de threads à utiliser [défaut: nombre de CPU].
-o, --output <dir>          Spécifie le dossier de sortie [défaut: eth_wallets].
-f, --format <format>       Choisit le format de sortie (txt, json, all) [défaut: txt].
-c, --check-balance         Vérifie le solde des adresses générées.
```

### Modes spéciaux
```
--zeros                     Score les adresses contenant le plus de zéros.
--leading <hex>             Score les adresses commençant par le caractère hex donné.
--mirror                    Score les adresses avec motif en miroir.
--notable                   Score les adresses avec des motifs remarquables (1337, 420, etc.).
--repeating <hex>           Score les adresses avec répétition du motif hex donné.
```

### Exemples

#### Préfixes communs
```
# Adresse commençant par 0xcafe
python eth_vanity.py -p cafe

# Adresse commençant par 0xdead
python eth_vanity.py -p dead

# Adresse commençant par 0xf00d
python eth_vanity.py -p f00d

# Adresse commençant par 0xb00b
python eth_vanity.py -p b00b
```

#### Suffixes intéressants
```
# Adresse se terminant par 1337
python eth_vanity.py -s 1337

# Adresse se terminant par beef
python eth_vanity.py -s beef

# Adresse se terminant par 0000
python eth_vanity.py -s 0000
```

#### Combinaisons
```
# Adresse commençant par bad et se terminant par food
python eth_vanity.py -p bad -s food

# Adresse commençant par ace et se terminant par 777
python eth_vanity.py -p ace -s 777
```

#### Motifs regex
```
# Adresse contenant une répétition de "00"
python eth_vanity.py -r "00{4,}"

# Adresse contenant le motif "1337"
python eth_vanity.py -r "1337"

# Adresse contenant une alternance de 1 et 0
python eth_vanity.py -r "(10){3,}"
```

#### Options de performance
```
# Utiliser 8 threads
python eth_vanity.py -p cafe -t 8

# Générer en continu plusieurs adresses correspondantes
python eth_vanity.py -p dead -m

# Enregistrer en format JSON
python eth_vanity.py -p face -f json

# Vérifier le solde ETH des adresses générées
python eth_vanity.py -p 1337 -c
```

## Performances et astuces

- **Temps de recherche**: Le temps de recherche augmente exponentiellement avec la longueur du préfixe/suffixe.
  - 3 caractères: quelques secondes à minutes
  - 4 caractères: minutes à heures
  - 5 caractères: heures à jours
  - 6+ caractères: jours à semaines

- **Optimisation**: Augmentez le nombre de threads pour accélérer la recherche, mais ne dépassez pas le nombre de cœurs de votre CPU.

- **Stockage**: Les portefeuilles trouvés sont stockés dans le dossier spécifié (par défaut: eth_wallets).

## Complexité et probabilité

La probabilité de trouver une adresse avec un préfixe spécifique de longueur N est de 1/(16^N).

| Longueur  | Probabilité  | Nombre moyen d'essais |
|-----------|--------------|----------------------|
| 1 caractère | 1/16        | 16                   |
| 2 caractères | 1/256      | 256                  |
| 3 caractères | 1/4,096    | 4,096                |
| 4 caractères | 1/65,536   | 65,536               |
| 5 caractères | 1/1,048,576| 1,048,576            |
| 6 caractères | 1/16,777,216| 16,777,216          |

## Sécurité

- **Confidentialité**: Les clés privées générées ne sont jamais partagées en ligne.
- **Stockage**: Toutes les clés sont stockées localement dans le dossier de sortie.
- **Validation**: Vérifiez toujours que la clé privée générée correspond bien à l'adresse publique.

## À propos

Ce générateur d'adresses vanity Ethereum est conçu pour être simple, rapide et personnalisable. Il utilise la bibliothèque web3.py et eth_account pour générer des paires de clés Ethereum de manière cryptographiquement sécurisée.

## Avertissement

Toujours vérifier que la clé privée générée par ce programme correspond bien à l'adresse publique annoncée en l'important dans un portefeuille de votre choix. Comme tout logiciel, ce programme peut contenir des bugs.

N'utilisez que des adresses vanity pour des portefeuilles dont vous maîtrisez la sécurité et ne les utilisez pas pour stocker de grandes quantités de cryptomonnaies sans prendre les précautions nécessaires.
