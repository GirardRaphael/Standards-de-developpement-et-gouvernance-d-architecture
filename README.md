# Portail de demandes de service

Projet de TP en Python 3.12 et SQLite, sans dépendance applicative externe. La CLI sert de transport pour démontrer les mêmes contrôles côté application qu’une interface Web appellerait.

## Démarrage

Depuis la racine du projet, dans un terminal interactif avec Python 3.12.

```sh
python -m portal init
python -m portal --user employe create --key demande-001
python -m portal --user employe list --status NEW
```

Copier les jetons générés à l’initialisation dans un emplacement privé. La CLI demande le jeton du compte à chaque commande. Utiliser des données fictives pour la démonstration. Les fichiers locaux résident dans `instance/`. Pour un second essai, placer `--instance autre-instance` avant la sous-commande et utiliser un nouveau répertoire privé.

| Élément | Fichier |
|---|---|
| Fiche de conception et diagramme | [docs/Conception.pdf](docs/Conception.pdf) |
| Contrats | [docs/contrats.md](docs/contrats.md) |
| Décision d’architecture | [docs/adr-001.md](docs/adr-001.md) |
| Démonstration et modification en direct | [docs/demonstration.md](docs/demonstration.md) |
| Pipeline et preuve locale | [docs/ci.md](docs/ci.md), [docs/verification-ci.txt](docs/verification-ci.txt) |
| Invariants et accès | `portal/domain.py`, `portal/service.py` |
| Ports et adaptateurs | `portal/ports.py`, `portal/sqlite.py`, `portal/__main__.py` |

## Vérifications

Dans Bash, avec Python 3.12. Sous Windows, exécuter les commandes dans WSL ou Git Bash avec un interpréteur Python 3.12 disponible.

```sh
python -m venv .venv
source .venv/bin/activate
bash checks.sh
```

L’archive contient un bundle Git. Pour obtenir le dépôt avec son historique, depuis le dossier décompressé, exécuter `git clone portail-historique.bundle portail-git`.
