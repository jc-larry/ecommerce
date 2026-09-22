# Dataset pareado

Agrega aqui las muestras supervisadas antes del fine-tuning:

```text
dataset_pareado/
|- train/<sample_id>/metadata.json
|- val/<sample_id>/metadata.json
`- test/<sample_id>/metadata.json
```

Cada `<sample_id>` debe contener `person.jpg`, `cloth.jpg`, `target.jpg`, `cloth_mask.png`, `human_parse.png`, `pose.json` y `metadata.json`.

No repitas la misma identidad de persona entre `train`, `val` y `test`.
