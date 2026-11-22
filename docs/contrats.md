# Contrats du portail

Le transport public est la CLI `python -m portal --user <compte> …`. Les exemples JSON décrivent les commandes après authentification. Le transport obtient le rôle du registre de l’instance après vérification du jeton. L’identité et le rôle ne sont jamais fournis dans la charge utile. Les arguments manquants de la CLI donnent le code de sortie 2.

## Créer une demande

```sh
python -m portal --user employe create --key creation-001
```

```json
{"operation":"create","key":"creation-001","title":"Accès VPN","description":"Connexion refusée"}
```

Le titre et la description sont saisis au clavier. Après retrait des espaces aux extrémités, les champs sont obligatoires et limités à 120 et 4 000 caractères. Tout compte authentifié peut créer. La demande hérite du propriétaire authentifié et reçoit l’état `NEW`. L’opération ne référence aucune ressource préexistante.

```json
{"request_id":"362af926fbab4d92babefe016af22fe6","status":"NEW","replayed":false}
```

## Changer d’état

```sh
python -m portal --user agent status 362af926fbab4d92babefe016af22fe6 IN_PROGRESS --key demarrer-001
```

```json
{"operation":"status","key":"demarrer-001","request_id":"362af926fbab4d92babefe016af22fe6","status":"IN_PROGRESS"}
```

L’identifiant (1 à 64 caractères) et l’état cible (valeur exacte de l’énumération) sont obligatoires. L’agent doit être affecté à la demande. Le superviseur peut faire progresser toute demande et lui seul peut la fermer. Un employé reçoit `ACCES_REFUSE`. Pour le personnel de traitement, une demande absente donne `INTROUVABLE`. Une transition interdite donne `CONFLIT`. Réponse ci-dessous pour une demande préalablement affectée.

```json
{"request_id":"362af926fbab4d92babefe016af22fe6","status":"IN_PROGRESS","replayed":false}
```

## Répétition et erreurs

La clé est obligatoire pour chaque écriture et contient de 1 à 128 caractères après normalisation. Elle est unique dans l’espace du compte. Si l’accès est toujours autorisé, renvoyer la même commande canonique avec la même clé retourne l’identifiant et l’état originaux avec `replayed: true`. Une autre commande avec la même clé donne `CONFLIT` si ses champs, son accès et la ressource sont valides. Les rejets ne consomment pas la clé. Une affectation modifiée peut révoquer l’accès à un rejeu.

| Code | Condition | Sortie |
|---|---|---|
| Succès | Commande appliquée ou déjà appliquée | JSON, code 0 |
| VALIDATION | Valeur manquante, invalide ou trop longue | Message, code 1 |
| ACCES_REFUSE | Identification, rôle ou accès à l’action insuffisant | Message, code 1 |
| INTROUVABLE | Identifiant absent ou demande d’autrui consultée par un employé | Message, code 1 |
| CONFLIT | Transition, affectation ou réutilisation de clé incompatible | Message, code 1 |
| INDISPONIBLE | Échec de persistance | Message, code 1. Reprendre avec la même clé. |

Les autres commandes sont `get ID`, `list [--status ÉTAT]`, `assign ID AGENT --key CLÉ` et `note ID --key CLÉ`. La liste renvoie les identifiants, titres et états. La consultation omet les notes pour les comptes sans accès. La note est saisie au clavier et limitée à 2 000 caractères.
