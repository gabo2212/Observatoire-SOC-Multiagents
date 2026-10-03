# Mes objectifs Git
Git pour débutants — cours pratique et 
commandes essentielles
Niveau : débutant
Durée : 2 à 4 heures
Terminal utilisé : PowerShell
Objectif : apprendre à enregistrer, consulter, partager et restaurer les versions d'un projet avec 
Git.

1. Qu'est-ce que Git ?
Git est un système de gestion de versions. Il permet de :
conserver l'historique d'un projet ;
savoir qui a modifié quoi et pourquoi ;
revenir à une ancienne version ;
travailler sur plusieurs fonctionnalités séparément ;
collaborer avec d'autres personnes ;
synchroniser un projet avec GitHub, GitLab ou un autre serveur.
Git fonctionne d'abord localement sur votre ordinateur. GitHub est un service Web pouvant 
héberger un dépôt Git. Git et GitHub ne sont donc pas la même chose.

2. Le vocabulaire essentiel
Terme Signification
Dépôt ou repository Dossier suivi par Git
Commit Enregistrement d'une version du projet
Branche Ligne de développement indépendante

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 1/22


Terme Signification
main Nom fréquent de la branche principale
Working directory Fichiers présents dans le dossier de travail
Staging area Zone de préparation du prochain commit
Remote Copie distante du dépôt, par exemple sur GitHub
origin Nom donné habituellement au remote principal
HEAD Commit actuellement sélectionné
Merge Fusion de deux branches
Conflict Modifications incompatibles que Git ne peut fusionner seul

Le parcours normal d'un fichier est :

Fichier modifié → git add → zone de préparation → git commit → historique

Avec un serveur distant :

Dépôt distant ── git pull/fetch ──▶ Dépôt local 
Dépôt local ── git push ────────▶ Dépôt distant

3. Installer et configurer Git
Vérifier l'installation

git - version

Configurer son identité
Cette information est enregistrée dans les commits.

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 2/22


git config - global user.name "Votre Nom"
git config - global user.email "vous@example.com"

Afficher la configuration :

git config - global - list

Configurer main comme nom initial des nouvelles branches :

git config - global init.defaultBranch main

Utilisez l'adresse liée à votre compte GitHub si vous souhaitez que GitHub associe 
correctement vos commits à votre profil. GitHub permet aussi d'utiliser une adresse privée
noreply .

4. Créer ou obtenir un dépôt
Il existe deux façons principales de commencer.
Option A — Transformer un dossier existant en dépôt 
Placez-vous dans le dossier du projet :

cd D:\chemin\vers\mon-projet 
git init

git init crée un dossier caché .git contenant l'historique et la configuration locale.
Option B — Copier un dépôt existant

git clone https: github.com/utilisateur/projet.git 
cd projet

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 3/22


git clone copie les fichiers, l'historique, les branches accessibles et la configuration du 
remote origin .

N'exécutez pas git init après git clone : le dépôt est déjà initialisé.

5. Le cycle de travail fondamental
5.1 Observer l'état du dépôt

git status

Version plus courte :

git status - short

Symboles fréquents :

Symbole Signification
? Fichier non suivi
M Fichier modifié
A Nouveau fichier préparé
D Fichier supprimé

5.2 Examiner les modifications
Modifications qui ne sont pas encore préparées :

git diff

Modifications déjà préparées avec git add :

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 4/22


git diff - staged

5.3 Préparer les fichiers
Préparer un fichier précis :

git add README.md

Préparer plusieurs fichiers précis :

git add README.md app.py

Préparer toutes les modifications du dossier courant :

git add .

Il est plus prudent d'exécuter git status et git diff avant git add . afin de ne pas 
inclure un secret ou un fichier inutile.
5.4 Créer un commit

git commit -m "Ajoute la page de connexion"

Un bon message est court, précis et explique le changement :

Ajoute la validation du formulaire 
Corrige le calcul du total 
Documente l'installation du projet

Évitez les messages vagues comme update , changes ou test .
5.5 Vérifier l'historique

git log

Version compacte :

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 5/22


git log - oneline

Historique avec les branches :

git log - oneline - graph - decorate - all

Routine quotidienne minimale

git status 
git diff
git add README.md 
git diff - staged 
git commit -m "Améliore les instructions"
git status

6. Ignorer certains fichiers
Le fichier .gitignore indique les fichiers que Git ne doit pas suivre. 
Exemple :

# Variables et secrets 
.env
.env.*

# Python 
__pycache__/ 
*.pyc
.venv/

# Node.js 
node_modules/

# Fichiers générés 
dist/
build/

# Éditeurs et système 
.vscode/

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 6/22


.DS_Store 
Thumbs.db

Ajoutez .gitignore avant le premier commit.

.gitignore n'arrête pas le suivi d'un fichier déjà enregistré. Pour retirer un fichier de Git tout 
en le conservant sur l'ordinateur :

git rm - cached .env

Si un secret a déjà été commité ou envoyé sur un serveur, le retirer du dernier commit ne suffit 
pas. Considérez-le comme compromis et remplacez immédiatement la clé ou le mot de passe.

7. Travailler avec les branches
Une branche permet de développer une fonctionnalité sans modifier immédiatement la 
branche principale.
Afficher les branches

git branch

Afficher les branches locales et distantes :

git branch - all

Créer une branche et s'y déplacer

git switch -c ajout-formulaire

Cette commande moderne remplace souvent :

git checkout -b ajout-formulaire

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 7/22


Changer de branche

git switch main

Ancienne syntaxe encore très utilisée :

git checkout main

Renommer une branche

git branch -m ancien-nom nouveau-nom

Fusionner une branche
Placez-vous d'abord dans la branche qui doit recevoir les modifications :

git switch main
git merge ajout-formulaire

Supprimer une branche locale fusionnée

git branch -d ajout-formulaire

-d refuse généralement de supprimer une branche non fusionnée. -D force la suppression et 
peut faire perdre des commits difficiles à retrouver ; utilisez-le seulement lorsque vous 
comprenez les conséquences.

8. Utiliser GitHub ou un autre dépôt distant
Voir les remotes

git remote -v

Ajouter un remote

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 8/22


Après avoir créé un dépôt vide sur GitHub :

git remote add origin https: github.com/utilisateur/projet.git

Envoyer la branche principale

git push -u origin main

L'option -u associe la branche locale à la branche distante. Les prochains envois peuvent 
généralement utiliser :

git push

Télécharger les informations sans fusionner

git fetch origin

fetch met à jour la connaissance des branches distantes sans modifier vos fichiers de travail.
Télécharger et intégrer les changements

git pull

pull effectue généralement un fetch , puis intègre les changements dans la branche active.
Envoyer une nouvelle branche

git push -u origin ajout-formulaire

Supprimer une branche distante

git push origin - delete ajout-formulaire

Flux de collaboration courant

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 9/22


git switch main 
git pull
git switch -c correction-menu
# Modifier les fichiers
git status
git add .
git commit -m "Corrige le menu mobile" 
git push -u origin correction-menu

Créez ensuite une pull request sur GitHub afin de faire réviser et fusionner la branche.

9. Annuler sans perdre son travail
Avant toute annulation, utilisez :

git status 
git diff
git log - oneline

Retirer un fichier de la zone de préparation
Le fichier reste modifié sur l'ordinateur :

git restore - staged README.md

Abandonner les changements non commités d'un fichier

git restore README.md

Cette commande remplace les modifications locales par la dernière version enregistrée. Les 
changements non commités peuvent être perdus.
Corriger le dernier commit 
Après avoir oublié un fichier :

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 10/22


git add fichier-oublie.md
git commit - amend - no-edit

Modifier uniquement le message :

git commit - amend -m "Nouveau message plus précis"

Évitez de modifier un commit déjà partagé, car son identifiant change.
Créer un commit qui annule un ancien commit

git revert IDENTIFIANT_DU_COMMIT

revert est généralement le choix sûr pour un historique déjà partagé : il crée un nouveau 
commit inverse sans réécrire l'historique.
Replacer une branche sur un ancien commit

git reset - soft IDENTIFIANT_DU_COMMIT 
git reset - mixed IDENTIFIANT_DU_COMMIT 
git reset - hard IDENTIFIANT_DU_COMMIT

Différences :

Mode Commit retiré Zone de préparation Fichiers de travail
- soft Oui Conservée Conservés
- mixed Oui Réinitialisée Conservés
- hard Oui Réinitialisée Écrasés

git reset - hard peut détruire les modifications non enregistrées. Ne l'utilisez pas comme 
commande de nettoyage automatique.

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 11/22


10. Mettre temporairement des changements de côté
stash est utile lorsqu'un travail n'est pas prêt à être commité et que vous devez changer de 
branche.
Mettre les modifications de côté :

git stash push -m "Travail temporaire sur le formulaire"

Inclure aussi les fichiers non suivis :

git stash push -u -m "Travail temporaire"

Afficher les stash :

git stash list

Réappliquer le plus récent sans le supprimer de la liste :

git stash apply

Réappliquer et retirer de la liste :

git stash pop

Supprimer un stash précis :

git stash drop 'stash@{0}'

Un stash est temporaire. Pour un travail important, préférez une branche et un commit 
clairement nommé.

11. Comprendre et résoudre un conflit
Un conflit survient lorsque Git ne peut pas choisir entre deux modifications.

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 12/22


Le fichier peut contenir :

<<<<<<< HEAD
Texte de la branche actuelle
=======
Texte de l'autre branche 
>>>>>>> ajout-formulaire

Procédure :
1. exécutez git status ;
2. ouvrez chaque fichier en conflit ;
3. choisissez ou combinez les bonnes lignes ;
4. retirez les marqueurs <<<<<<< , ======= et >>>>>>> ; 
5. testez le projet ;
6. préparez les fichiers résolus ;
7. terminez la fusion.

git add fichier-resolu.md 
git commit

Annuler la fusion en cours :

git merge - abort

Ne choisissez pas automatiquement « accepter tout » sans comprendre les deux versions.

12. Rechercher dans l'historique
Afficher un commit :

git show IDENTIFIANT_DU_COMMIT

Afficher l'historique d'un fichier :

git log - oneline - README.md

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 13/22


Afficher les modifications de chaque commit :

git log -p

Rechercher un texte dans les fichiers suivis :

git grep "mot recherché"

Afficher l'auteur de chaque ligne :

git blame README.md

git blame donne du contexte historique. Il ne devrait pas servir à blâmer une personne.

13. Comparer des versions
Comparer le travail actuel au dernier commit :

git diff HEAD

Comparer deux commits :

git diff COMMIT_1 COMMIT_2

Comparer deux branches :

git diff main. ajout-formulaire

Voir seulement les noms des fichiers modifiés :

git diff - name-only main. ajout-formulaire

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 14/22


14. Utiliser les tags
Un tag marque une version importante, par exemple v1.0.0 . 
Créer un tag annoté :

git tag -a v1.0.0 -m "Première version stable"

Afficher les tags :

git tag

Envoyer un tag :

git push origin v1.0.0

Envoyer tous les tags :

git push origin - tags

15. Commandes utiles pour les fichiers
Déplacer ou renommer un fichier suivi :

git mv ancien-nom.md nouveau-nom.md

Supprimer un fichier suivi :

git rm fichier.md

Retirer un fichier du suivi sans le supprimer localement :

git rm - cached fichier.md

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 15/22


Afficher les fichiers suivis :

git ls-files

16. merge , rebase et cherry-pick
Ces commandes ne répondent pas exactement au même besoin.

merge
Fusionne l'historique d'une branche dans une autre. C'est le choix le plus simple pour
commencer.

git switch main
git merge ajout-formulaire

rebase
Replace les commits d'une branche sur une autre base afin de créer un historique plus linéaire.

git switch ajout-formulaire 
git rebase main

Un rebase réécrit les identifiants des commits. Évitez de rebaser des commits partagés avec 
d'autres personnes, sauf si l'équipe suit cette convention.
En cas de conflit :

git add fichier-resolu.md 
git rebase - continue

Pour abandonner :

git rebase - abort

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 16/22


cherry-pick
Copie un commit précis sur la branche active :

git cherry-pick IDENTIFIANT_DU_COMMIT

Utilisez-le lorsqu'un changement isolé est nécessaire sans fusionner toute la branche.

17. Petit exercice pratique
Créez un dossier de test qui ne contient aucun fichier important.
Étape 1 — Initialiser

New-Item -ItemType Directory -Path git-exercice 
Set-Location git-exercice
git init

Étape 2 — Créer un premier fichier
Créez README.md dans VS Code avec :

# Mon exercice Git

Ce projet sert à apprendre Git.

Puis :

git status
git add README.md
git diff - staged
git commit -m "Crée le fichier README"

Étape 3 — Créer une branche

git switch -c ajout-objectifs

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 17/22


Ajoutez au fichier :

## Objectifs

- créer des commits ;
- utiliser une branche ; 
- fusionner le travail.

Puis :

git add README.md
git commit -m "Ajoute les objectifs du projet"

Étape 4 — Fusionner

git switch main
git merge ajout-objectifs
git branch -d ajout-objectifs

Étape 5 — Examiner le résultat

git status
git log - oneline - graph - decorate - all

Critères de réussite
[ ] Le dépôt se trouve sur la branche main .
[ ] Le dossier de travail est propre.
[ ] L'historique contient deux commits.
[ ] Le fichier contient le titre, la description et les objectifs. 
[ ] La branche temporaire a été fusionnée puis supprimée.

18. Erreurs fréquentes
« Not a git repository »
Vous n'êtes pas dans un dépôt Git.

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 18/22


Get-Location 
Get-ChildItem -Force

Déplacez-vous dans le bon dossier ou utilisez git init si vous créez réellement un nouveau 
dépôt.
« Nothing to commit »
Il n'existe aucune modification préparée. Vérifiez :

git status

Le push est rejeté
Le dépôt distant contient peut-être des commits absents localement.

git pull

Résolvez les conflits éventuels, puis recommencez git push . Ne forcez pas le push sans 
comprendre pourquoi il a été rejeté.
Git demande toujours un mot de passe
Les services comme GitHub n'acceptent généralement pas le mot de passe du compte pour les 
opérations Git en HTTPS. Utilisez le gestionnaire d'informations d'identification, 
l'authentification proposée par l'outil, un jeton autorisé ou une clé SSH selon les règles de 
votre organisation.
Un fichier secret apparaît dans Git
1. Retirez-le du suivi avec git rm - cached .
2. Ajoutez-le à .gitignore .
3. Commitez la correction.
4. Si le secret a déjà été partagé, révoquez-le et créez-en un nouveau.

19. Bonnes pratiques

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 19/22


exécuter souvent git status ;
examiner git diff avant de préparer les fichiers ;
créer de petits commits cohérents ;
écrire des messages précis ;
ne jamais commiter de mots de passe ou de clés ;
utiliser une branche par fonctionnalité ou correction ;
actualiser main avant de commencer un nouveau travail ;
tester le projet avant de fusionner ;
relire une pull request avant de l'approuver ;
préférer git revert pour annuler un commit déjà partagé ;
sauvegarder le travail important dans un commit plutôt que seulement un stash ; 
ne pas utiliser reset - hard ou un push forcé sans comprendre les effets.

20. Aide intégrée
Afficher l'aide générale :

git help

Afficher l'aide d'une commande :

git help commit 
git help branch

Aide courte dans le terminal :

git commit -h

Git contient de nombreuses commandes spécialisées. Il n'est pas nécessaire de toutes les 
mémoriser : maîtrisez d'abord status , diff , add , commit , log , switch , merge , pull 
et push .

21. Aide-mémoire

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 20/22


Objectif Commande
Initialiser un dépôt git init
Copier un dépôt git clone URL
Voir l'état git status
Voir les modifications git diff
Préparer un fichier git add fichier
Préparer tous les changements git add .
Créer un commit git commit -m "Message"
Voir l'historique git log - oneline
Créer une branche git switch -c nom
Changer de branche git switch nom
Fusionner une branche git merge nom
Voir les remotes git remote -v
Télécharger sans fusionner git fetch
Télécharger et intégrer git pull
Envoyer les commits git push
Retirer du staging git restore - staged fichier
Abandonner une modification git restore fichier
Annuler un commit partagé git revert commit
Mettre le travail de côté git stash
Réappliquer le stash git stash pop
Afficher un commit git show commit

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 21/22


Objectif Commande
Marquer une version git tag -a v1.0.0 -m "Version 1"

Quiz rapide
1. Quelle est la différence entre Git et GitHub ?
2. À quoi sert la zone de préparation ?
3. Quelle commande montre les fichiers modifiés ?
4. Quelle commande prépare un fichier ?
5. Quelle commande enregistre une version ?
6. Pourquoi créer une branche ?
7. Quelle est la différence entre fetch et pull ?
8. Quelle commande annule prudemment un commit déjà partagé ? 
9. Pourquoi reset - hard est-il dangereux ?
10. Que faut-il faire si un secret a été envoyé sur GitHub ?
Réponses

10/3/26, 9:20 AM Git pour débutants — cours pratique et commandes essentielles

file:///D:/hamedexercies/cours_git_debutant.html 