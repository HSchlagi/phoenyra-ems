# 🔋 PowerFlow_Diagram_CursorAI.md

## Zweck
Erzeugt ein interaktives **Stromfluss-Diagramm (Sankey-Style)** zur Visualisierung von PV-, Batterie-, Netz- und Lastströmen.  
Die Darstellung ist an Phoenyra EMS angepasst und kann in Dashboards oder Monitoring-Views eingebettet werden.

---

## ⚙️ Voraussetzungen

```bash
pip install pandas plotly
```

Optional für Web-Integration:
```bash
pip install flask
```

---

## 📊 Python-Code

```python
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# Beispiel-Daten (kWh pro Energiepfad)
data = {
    "Quelle": ["PV", "PV", "Netz", "Batterie"],
    "Ziel":   ["Batterie", "Last", "Last", "Last"],
    "Energie_kWh": [2.05, 0.10, 20.82, 1.52]
}

df = pd.DataFrame(data)

# Knoten ermitteln
nodes = list(pd.unique(df[['Quelle', 'Ziel']].values.ravel()))

# Indizes für Quelle/Ziel berechnen
df["Quelle_idx"] = df["Quelle"].apply(lambda x: nodes.index(x))
df["Ziel_idx"]   = df["Ziel"].apply(lambda x: nodes.index(x))

# Sankey-Plot definieren
fig = go.Figure(data=[go.Sankey(
    arrangement="snap",
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=nodes,
        color=["#FFD700", "#00FF7F", "#1E90FF", "#9370DB"]
    ),
    link=dict(
        source=df["Quelle_idx"],
        target=df["Ziel_idx"],
        value=df["Energie_kWh"],
        color="rgba(100,150,255,0.4)"
    )
)])

fig.update_layout(
    title_text="⚡ Stromflussdiagramm – Tagesübersicht",
    font=dict(size=14),
    template="plotly_dark"
)

# Ausgabe
fig.show()

# Optional: HTML export
html_path = "powerflow_diagram.html"
pio.write_html(fig, file=html_path, auto_open=False)
print(f"HTML exportiert nach: {html_path}")
```

---

## 📈 Ergebnis

- Interaktives Sankey-Diagramm im Dark-Mode  
- Zeigt Stromfluss von PV → Batterie/Last, Netz → Last, Batterie → Last  
- Tooltipps mit kWh-Werten  
- Farben frei definierbar (Hex- oder RGBA-Farben)  

---

## 🧩 Integration in Phoenyra EMS

### Variante 1 – Lokaler Python-Render
1. Datei speichern unter `phoenyra/visuals/powerflow.py`
2. Im EMS-Backend einbetten:
   ```python
   from visuals.powerflow import render_powerflow
   html = render_powerflow(data_dict)
   ```
3. Ergebnis als HTML im Frontend-Panel laden.

### Variante 2 – n8n-Workflow
1. „Execute Python“-Node einfügen  
2. Obigen Code dort einfügen  
3. Ergebnis-HTML über HTTP-Response-Node zurückgeben  
4. Im Dashboard via iframe einbinden.

### Variante 3 – Flask-API (optional)
```python
from flask import Flask, send_file
app = Flask(__name__)

@app.route("/powerflow")
def serve_powerflow():
    from powerflow import create_powerflow
    html_path = create_powerflow()
    return send_file(html_path)
```

---

## 📘 Tipps

- Für Zeitreihen-Aggregation: pandas `resample('15min')`  
- Für dynamische Animation: Plotly Express + Frames  
- Für mehrere Standorte: Filter mit Dropdown (Plotly Dash)

---

**Autor:** Phoenyra Engineering  
**Lizenz:** Open Integration License (OIL-1.0)  
**Version:** 1.0.0  
**Datum:** 2025-11-11
