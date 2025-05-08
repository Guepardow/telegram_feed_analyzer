# Evaluation

All these results are with either baseline or PROMPT_COMBINED.
Evaluator based on gemini-2.5-flash-preview-04-17

## Translation

|       Method A         |     Method B                    |  A  | SAME |  B  |
|------------------------|---------------------------------|-----|------|-----|
| gemini-2.0-flash       | gemini-1.5-flash                |  22 |   7  |  21 |
| gemini-2.0-flash       | gemini-2.5-flash-preview-04-17  |  17 |  12  |  21 |
| gemini-2.0-flash       | gemini-2.0-flash-lite           |  19 |  10  |  21 |
| gemini-2.0-flash-lite  | gemini-1.5-flash                |  22 |  10  |  18 |
| gemini-2.0-flash-lite  | gemini-2.5-flash-preview-04-17  |  15 |  13  |  22 |

## Geolocation

Results on sample50:
|         Model                  |   FP  |   FN  | Average distance |
|--------------------------------|-------|-------|------------------|
| baseline                       |  39   | **3** |    1973.8 km     |
| gemini-2.0-flash-lite          |   9   |   8   |   **3.0 km**     |
| gemini-2.0-flash               |  10   |   7   |   **3.3 km**     |
| gemini-1.5-flash               |  10   |   7   |       7.4 km     |
| gemini-2.5-flash-preview-04-17 | **5** |   5   |   **3.7 km**     |

## Sentiment analysis

|       Method A         |     Method B                    |   A   | SAME |  B  |
|------------------------|---------------------------------|-------|------|-----|
| gemini-2.0-flash       | gemini-2.0-flash-lite           |**30** |  11  |  6  |
