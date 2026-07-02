# Специфікація формату JSON конфігурації (Workload Schema)

```
GroupsConfig (Кореневий об'єкт)
 └── groups (Масив об'єктів GroupData)
      ├── group_name (Рядок, назва папки/групи)
      └── prompts (Масив об'єктів PromptData)
           ├── name (Рядок, унікальна назва таски)
           ├── pos (Рядок, позитивний промпт)
           ├── neg (Рядок, негативний промпт, опціонально)
           ├── upscale (Булеве значення, апскейл, опціонально)
           ├── rembg (Булеве значення, видалення фону, опціонально)
           └── copy_style (Булеве значення, копіювання стилю, опціонально)
```

---

## Опис полів конфігурації

### 1. `GroupsConfig` (Кореневий об'єкт)
Головний об'єкт конфігурації.
* **`groups`** (array of `GroupData`, обов'язкове): Список груп генерації. За замовчуванням порожній список `[]`.

### 2. `GroupData`
Описує окрему групу промптів. Використовується для організації файлової структури результатів (зображення зберігаються у відповідних папках).
* **`group_name`** (string, опціонально): Назва групи. Використовується для створення папки збереження результатів. За замовчуванням: `"unnamed_group"`.
* **`prompts`** (array of `PromptData`, обов'язкове): Список окремих промптів для генерації в межах цієї групи.

### 3. `PromptData`
Структура даних для одного запиту генерації зображення. Завдяки налаштуванню `populate_by_name = True` у Pydantic, JSON може містити як оригінальні імена полів моделі, так і їхні аліаси.
* **`name`** (string, обов'язкове): Унікальний ідентифікатор/назва зображення. Використовується для формування імені файлу (наприклад, `{name}.png`).
* **`pos`** (або **`positive`**) (string, обов'язкове): Позитивний текстовий промпт, що описує бажаний вміст зображення.
* **`neg`** (або **`negative`**) (string, опціонально): Негативний текстовий промпт, що описує елементи, які слід виключити. За замовчуванням: `""`.
* **`upscale`** (boolean, опціонально): Прапорець для запуску апскейлу згенерованого зображення. За замовчуванням: `false`.
* **`rembg`** (boolean, опціонально): Прапорець для видалення заднього фону. За замовчуванням: `false`.
* **`copy_style`** (boolean, опціонально): Прапорець для спроби копіювання стилю з референсного зображення. За замовчуванням: `false`.

---

## Приклад файлу конфігурації (`flux_workload.json`)

```json
{
  "groups": [
    {
      "group_name": "cyberpunk_landscapes",
      "prompts": [
        {
          "name": "cyberpunk_city_sunset",
          "pos": "A futuristic city at sunset, neon lights, highly detailed, 8k resolution",
          "neg": "blurry, low quality, distorted, humans",
          "upscale": true,
          "rembg": false,
          "copy_style": false
        },
        {
          "name": "neon_street_rain",
          "pos": "A neon-lit street in Tokyo under heavy rain, cinematic reflection",
          "upscale": false
        }
      ]
    },
    {
      "group_name": "fantasy_characters",
      "prompts": [
        {
          "name": "elven_mage",
          "pos": "A portrait of an elf mage casting a glowing blue spell, fantasy art, highly detailed"
        }
      ]
    }
  ]
}
```