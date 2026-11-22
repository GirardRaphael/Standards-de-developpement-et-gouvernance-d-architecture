# Vérifications continues

Git conserve les commits. GitHub Actions exécute les contrôles à chaque push ou pull request selon `.github/workflows/ci.yml`. Le jeton du workflow dispose d’un accès en lecture au dépôt et les actions sont référencées par commit. Le job n’utilise aucun jeton applicatif.

`bash checks.sh` installe Ruff, vérifie le formatage, applique le lint, exécute les tests, compile le paquet Python et vérifie l’entrée CLI et les espaces dans le diff. Chaque échec interrompt le job.

Pour rendre ces vérifications obligatoires sur GitHub, protéger `main` avec une règle qui impose une pull request et le statut `checks` réussi avant la fusion, y compris pour les comptes disposant normalement d’un droit de contournement. Cette configuration relève du dépôt de destination.

La sortie jointe provient du même script que le workflow, exécuté localement dans un environnement virtuel. Aucun run GitHub Actions ni règle de protection distante n’a été vérifié.

[Renforcement de la sécurité de GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
