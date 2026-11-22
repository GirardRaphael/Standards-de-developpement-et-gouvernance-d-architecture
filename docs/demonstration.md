# Démonstration en classe · 7 minutes

Préparer une instance avec `python -m portal init`. Garder les jetons hors de l’écran partagé. Dans les commandes suivantes, remplacer `ID` par l’identifiant retourné par la création et saisir chaque jeton à l’invite privée.

| Temps | Manipulation | Résultat attendu |
|---|---|---|
| 0–1 min | Ouvrir le diagramme dans la fiche | Décrire le contrat CLI, l’autorisation et le commit commun. |
| 1–2 min | `python -m portal --user employe create --key demo-1`, puis répéter avec le même titre et la même description | Même ID, `replayed: true` à la seconde demande. |
| 2–3 min | `python -m portal --user agent assign ID agent --key demo-2` puis `python -m portal --user agent status ID IN_PROGRESS --key demo-3` | Affectation puis traitement. |
| 3–4 min | `python -m portal --user agent note ID --key demo-4` et lire le détail avec `get ID` en tant qu’agent et employé | La note est présente dans une seule des deux réponses. |
| 4–5 min | `python -m portal --user agent status ID RESOLVED --key demo-5` puis tenter `python -m portal --user agent status ID CLOSED --key demo-6` | Résolution, puis refus d’accès. |
| 5–6 min | `python -m portal --user superviseur status ID CLOSED --key demo-7` puis `python -m portal --user employe list --status CLOSED` | Fermeture et demande visible dans la liste filtrée. |
| 6–7 min | `bash checks.sh` | Contrôles et tests, dont l’annulation d’une écriture partielle. |

## Changement en direct

Exemple demandé par l’enseignant : réserver la lecture des notes au superviseur. Dans `Service.get`, remplacer la condition de projection par `if actor.role != Role.SUPERVISOR:`. Dans `test_visibility_and_missing_request`, vérifier que l’agent affecté ne voit plus les notes et que le superviseur les voit toujours. Exécuter `bash checks.sh`. Cette règle concerne la réponse du cas d’utilisation, donc le format de stockage et l’ajout de notes restent compatibles.

Pour une panne contrôlée, exécuter `python -m unittest discover -s tests -k failed_receipt -v`. Le test provoque un échec après l’écriture de la demande, vérifie l’annulation et réessaie avec la même clé.
