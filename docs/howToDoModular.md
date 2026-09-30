# Comment modulariser un notebook — expliqué simplement (méthode Feynman)

> Pour junior. Objectif : passer de `notebooks/customer_churn.ipynb`
> (brouillon qui marche une fois) à `src/model_pipeline.py` + `main.py`
> (recette réutilisable qui marche tout le temps).
> En français, avec le code en anglais (convention).

---

## 0. L'idée en 30 secondes (l'analogie cuisine)

Un **notebook**, c'est comme cuisiner en jetant tout dans une casserole :
ça marche, mais tu ne peux pas réutiliser, partager ou automatiser.

Le **code modulaire**, c'est écrire la **recette** :

- chaque étape = une **fonction** (= un verbe : installer, préparer, entraîner, évaluer...),
- chaque fonction a des **entrées** (ingrédients) et une **sortie** (plat),
- un **chef d'orchestre** (`main.py`) appelle les étapes dans l'ordre.

Si tu peux expliquer chaque fonction en une phrase à un enfant de 10 ans,
c'est qu'elle est bien découpée. C'est ça, la technique Feynman.

Notre résultat dans ce projet :

```text
workshop_ml/
  src/
    model_pipeline.py   # les 6 fonctions (la recette)
  main.py               # le chef qui exécute la recette
  requirements.txt      # la liste des ingrédients (pour pip ; uv utilise pyproject.toml)
  models/
    classifier.joblib   # le gâteau final (modèle sauvegardé)
  notebooks/data/
    Churn_Modelling.csv # les ingrédients
```

---

## 1. Étape 1 — Repérer les blocs logiques (surligner avant de coder)

Ne code rien tout de suite. Ouvre le notebook et mets une couleur par bloc :

| Couleur | Bloc | Cellules du notebook churn | Devient |
|---|---|---|---|
| 🟪 Violet | Installer les dépendances | *(pas de cellule : le notebook suppose que le kernel a déjà pandas/sklearn)* | `install_dependencies()` — **job n°1**, `pip install -r requirements.txt` |
| 🟦 Bleu | Charger + nettoyer | `read_csv`, `info`, `isna`, `LabelEncoder Gender`, `drop(Surname, Geography, RowNumber, CustomerId)` | `prepare_data()` |
| 🟩 Vert | Entraîner | `train_test_split`, `RandomForestClassifier(...).fit()` | `prepare_data()` (split) + `train_model()` |
| 🟨 Jaune | Évaluer | `predict`, `accuracy_score`, `confusion_matrix`, `ConfusionMatrixDisplay` | `evaluate_model()` |
| 🟥 Rouge | Sauver / charger | `joblib.dump` / `joblib.load` | `save_model()` / `load_model()` |
| ⬜ Blanc | Explorer / dessiner | `barplot`, `pairplot`, `pie`, `df.head()` | **On ne module pas** : ça reste dans le notebook |

**Règle Feynman :** si deux cellules répondent à la même question
("mes données sont-elles propres ?", "mon modèle est-il bon ?"),
elles vont dans la même fonction.

---

## 2. Étape 2 — La règle d'or : une fonction = un verbe + entrée → sortie

Avant d'écrire, complète cette phrase pour chaque fonction :

> "Cette fonction prend **...** en entrée, fait **...**, et rend **...**."

Pour notre projet :

```text
install_dependencies(requirements="requirements.txt") → prend un fichier requirements, rend True (tout est installé)
prepare_data(csv_path)      → prend un chemin CSV, rend X_train, X_test, y_train, y_test
train_model(X_train, y_train) → prend des données d'entraînement, rend un modèle entraîné
evaluate_model(model, X_test, y_test) → prend un modèle + données test, rend des scores
save_model(model, path)     → prend un modèle, rend le chemin où il est sauvé
load_model(path)            → prend un chemin, rend le modèle rechargé
```

Si tu n'arrives pas à remplir la phrase, la fonction est trop grosse : coupe-la.

Exemple concret, avant (notebook, tout mélangé) :

```python
# notebook : variables globales, ordre implicite, impossible à réutiliser
df = pd.read_csv('data/Churn_Modelling.csv')
df['Gender'] = encoder.fit_transform(df['Gender'])
df = df.drop(['Surname','Geography'], axis=1)
x = df.drop(['Exited'], axis=1)
x.drop(columns=['RowNumber','CustomerId'], inplace=True)
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=1)
```

Après (modulaire, réutilisable) :

```python
from src.model_pipeline import prepare_data

X_train, X_test, y_train, y_test = prepare_data("notebooks/data/Churn_Modelling.csv")
# Même résultat, mais : testable, importable, paramétrable (test_size, random_state)
```

---

## 3. Étape 3 — Écrire `install_dependencies()` (job n°1, toujours en premier)

Le notebook n'a **aucune cellule** pour ça : il suppose que le kernel contient
déjà pandas, sklearn, seaborn... Sur une machine neuve (ou celle d'un collègue),
ça plante avec `ModuleNotFoundError`.

La version modulaire rend cette étape **explicite et première** :

```python
from src.model_pipeline import install_dependencies

install_dependencies()  # = pip install -r requirements.txt
# True → tout est installé, la suite peut tourner
```

Recette pas à pas :

1. **Crée `requirements.txt`** : la liste des ingrédients, avec versions minimi
   (`joblib>=1.6.0`, `pandas>=3.0.6`, `scikit-learn>=1.9.1`...).
   Elle miroite `pyproject.toml` pour que les utilisateurs `pip` et `uv`
   installent la même chose (`uv` utilise `uv sync`, `pip` utilise ce fichier).
2. **Écris la fonction** : elle vérifie que le fichier existe
   (`raise FileNotFoundError` sinon), puis lance
   `sys.executable -m pip install -r requirements.txt` via `subprocess`
   (donc ça installe dans **le bon** Python/venv, pas un autre).
   Astuce : les venvs créés par `uv` n'ont pas de module `pip`, donc la
   fonction bascule automatiquement sur `uv pip install --python ...`
   quand `pip` est absent — même appel, même résultat.
3. **Appelle-la en premier dans `main.py`** (avec `--skip-install` pour la sauter
   en CI ou quand tu as déjà fait `uv sync`).

**Pourquoi c'est le job n°1 ?** Sans ingrédients, pas de cuisine.
C'est le seul job qui ne dépend de rien et dont tout dépend.

---

## 4. Étape 4 — Écrire `prepare_data()` (la fondation)

C'est la fondation. Tout le reste en dépend.

Recette pas à pas :

1. **Copie** les cellules de chargement/nettoyage dans une nouvelle fonction.
2. **Remplace** les variables globales par des **paramètres** :
   `csv_path`, `test_size=0.2`, `random_state=1`.
3. **Retourne** au lieu d'afficher : `return X_train, X_test, y_train, y_test`
   (pas de `print(df.head())`, pas de `plt.show()` dans une fonction de préparation).
4. **Protège** l'entrée : `if not csv_path.is_file(): raise FileNotFoundError(...)`.
   Un junior comprend "fichier introuvable", pas `FileNotFoundError: [Errno 2]` seul.

Voir `src/model_pipeline.py::prepare_data` — chaque ligne du notebook y est
retrouvée, mais sans les `df`, `x`, `y` globaux.

---

## 5. Étape 5 — Écrire `train_model()` (la plus facile)

Le notebook fait :

```python
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(x_train, y_train)
```

La version modulaire ne fait QUE ça, mais en fonction pure :

```python
def train_model(X_train, y_train, n_estimators=100, random_state=42):
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
    model.fit(X_train, y_train)
    return model
```

**Pourquoi c'est mieux ?** Tu peux maintenant entraîner avec d'autres paramètres
sans toucher au code : `train_model(X_train, y_train, n_estimators=200)`.
Dans le notebook, il fallait éditer la cellule et tout ré-exécuter.

> Note MLOps : le notebook crée un `StandardScaler` avec `fit_transform`
> sur train **et** sur test séparément, puis ne l'utilise jamais.
> C'est une fuite de données (le scaler apprend du test) + du code mort
> (RandomForest n'a pas besoin de scaling). On l'a **volontairement retiré** —
> voir le docstring en haut de `model_pipeline.py`. Garder un bug pour être
> "fidèle" serait pire que le corriger en l'expliquant.

---

## 6. Étape 6 — Écrire `evaluate_model()` (rendre, pas juste afficher)

Erreur classique du débutant : la cellule affiche `85.55` mais ne **rend rien**.
Impossible de comparer deux modèles automatiquement.

Bonne version :

```python
metrics = evaluate_model(model, X_test, y_test)
print(metrics["accuracy"])  # 0.8555 → réutilisable en test, en CI, en MLflow...
```

Notre `evaluate_model()` fait les deux : elle **affiche** (pour l'humain :
accuracy, classification_report, confusion matrix) ET elle **retourne un dict**
(pour la machine : `{"accuracy": ..., "report": ..., "confusion_matrix": ...}`).

---

## 7. Étape 7 — Écrire `save_model()` / `load_model()` (le frigo)

Sans ça, tu dois ré-entraîner à chaque fois (5 min, 1 h, 1 jour...).
Avec ça, tu entraînes une fois et tu réutilises :

```python
save_model(model, "models/classifier.joblib")  # range le gâteau au frigo
model = load_model("models/classifier.joblib")  # ressors-le demain
assert model.predict(X_test[:5]).shape == (5,)   # il marche toujours
```

Détails qui comptent (déjà gérés dans notre code) :

- `filepath.parent.mkdir(parents=True, exist_ok=True)` → crée `models/` s'il manque.
- `joblib.dump(model, filepath)` en une ligne → remplace le `open()/close()`
  manuel du notebook (qui fuit si le code plante entre les deux).
- `load_model` lève un message clair si le fichier n'existe pas
  ("entraîne d'abord avec train_model + save_model") au lieu d'une stack trace brute.

---

## 8. Étape 8 — Relier avec `main.py` (le chef d'orchestre)

`model_pipeline.py` = les ingrédients + ustensiles.
`main.py` = l'ordre de cuisson. Il ne contient **aucune logique ML**,
juste des appels :

```python
install_dependencies(args.requirements)                  # 1. installer
X_train, X_test, y_train, y_test = prepare_data(args.data)  # 2. préparer
model = train_model(X_train, y_train)                        # 3. entraîner
evaluate_model(model, X_test, y_test)                        # 4. évaluer
save_model(model, args.model)                                # 5. sauver
```

Lance-le :

```bash
# --- Façon pip (venv classique) ---
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py --skip-install        # déjà installé ci-dessus, on saute le job 1

# --- Façon uv ---
uv sync                              # installe depuis pyproject.toml
uv run python main.py                # job 1 (pip install) + train + evaluate + save
uv run python main.py --skip-install # saute le job 1 (déjà installé via uv sync)
uv run python main.py --no-train     # réutilise models/classifier.joblib
uv run python main.py --help         # voir --requirements, --data, --model, --n-estimators...
```

**Règle :** si `main.py` importe `sklearn` directement ou dépasse ~80 lignes,
c'est qu'une logique a fuité hors des fonctions. Remets-la dans
`model_pipeline.py`. (Seule exception ici : `pandas` pour le mini DataFrame
de démo, qui évite le warning "valid feature names" de sklearn.)

---

## 9. Checklist finale (à cocher à chaque modularisation)

- [ ] Job n°1 `install_dependencies()` présent + `requirements.txt` à jour
      (miroir de `pyproject.toml` : `pip install -r requirements.txt`
      et `uv sync` installent la même chose).
- [ ] Imports **en haut** du module, sans doublons, sans imports morts
      (ici on a supprimé `LinearSVC`, `LinearRegression`, `Lasso` inutilisés).
- [ ] **Aucun chemin en dur** dans les fonctions : tout passe par paramètre
      avec une valeur par défaut (`DEFAULT_REQUIREMENTS_PATH`,
      `DEFAULT_DATA_PATH`, `DEFAULT_MODEL_PATH`).
- [ ] **Aucune variable globale** modifiée (`inplace=True` sur un global = interdit).
- [ ] Chaque fonction a **docstring + exemple** (`Args / Returns / Example`).
- [ ] `evaluate` **retourne** des chiffres, pas seulement des `print`.
- [ ] `if __name__ == "__main__":` présent dans `main.py` (jamais dans le module).
- [ ] `uv run python main.py` reproduit le score notebook (~85.5 % accuracy).
- [ ] `uv run python main.py --no-train` marche après le premier run
      (preuve que save/load sont corrects).
- [ ] `uv run python main.py --skip-install` marche aussi
      (preuve que le job 1 est bien optionnel).

---

## 10. Les 3 pièges vus dans ce notebook (et comment les éviter)

| Piège | Ce que faisait le notebook | Le réflexe modulaire |
|---|---|---|
| Scaler fitté 2× puis ignoré | `fit_transform(X_train)` + `fit_transform(X_test)`, jamais utilisé | Soit un `Pipeline([scaler, model])` avec `fit` sur train seul, soit rien si l'algo n'en a pas besoin (RandomForest). Jamais de `fit` sur le test. |
| `df.isnull` sans parenthèses | Renvoie la méthode, pas le résultat → check silencieusement faux | En module, chaque check est une vraie assertion ou n'existe pas. Relis : fonction ≠ valeur. |
| Chemin relatif fragile | `'data/Churn_Modelling.csv'` alors que le fichier est dans `notebooks/data/` | `Path(__file__).resolve().parents[1] / "notebooks" / "data" / ...` + paramètre `--data` modifiable. |

---

## 11. Pour aller plus loin (quand c'est maîtrisé)

1. Remplacer le `drop(Geography)` par un `OneHotEncoder` (le notebook jette de l'info).
2. Ajouter `pytest` : `assert prepare_data(...)` a les bonnes shapes,
   `assert evaluate_model(...)["accuracy"] > 0.80`.
3. Logger avec `logging` au lieu de `print`, tracker avec MLflow.
4. Geler les hyperparamètres dans un `config.yaml` au lieu d'arguments parseurs.

Mais d'abord : fais tourner `uv run python main.py`, lis `src/model_pipeline.py`
fonction par fonction, et réexplique chacune en une phrase. Si tu y arrives,
tu as compris la modularisation. 🎯
