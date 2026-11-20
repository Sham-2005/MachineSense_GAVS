# MachineSense

MachineSense is an offline-first predictive maintenance **prototype** for small factories. It simulates sensor readings for a powerloom, flour mill, and pump set, scores them with one Isolation Forest per machine, and demonstrates an owner-approved repair workflow. All sensor readings and technician/dealer replies are simulated; the app does not connect to or control real equipment.

## Run locally

Python 3.10 or newer is recommended.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Core scoring, charts, sample data, and repair logging work locally without external APIs. gTTS is optional at runtime: audio generation may require internet; if it is unavailable, the translated text remains visible. Google Maps links are optional conveniences.

## Demo script (about 2 minutes)

1. Choose **Powerloom 1**, select **Tamil**, and click **Inject bearing fault**.
2. Click **Simulate next day** several times. Watch vibration and temperature trend upward; the status moves to Watch/Alert and the story explains the measured deviations with a qualified likely cause.
3. Click **Yes, I heard noise** to add a human label. Click **Approve dispatch**; the app does not stop the machine.
4. Open **Dispatch**. Review the Tamil text message and optional voice, the technician candidate, and the dealer stock/price. Click **Accept** (or **Decline** to try the next technician).
5. Open **Repair & learning**, enter the confirmed cause/part/cost/downtime, and save. The case is stored in `data/repair_log.csv` and can inform future similar-case stories.
6. Open **Impact**. Adjust daily loss and avoided downtime to show illustrative savings and the before/after timeline.

To demonstrate the environmental risk-factor path, reset the demo, click **Inject dust**, then simulate a day. Dust increases and the story recommends checking/cleaning vents without claiming dust caused the anomaly.

## Architecture

```text
Sidebar simulator controls
          |
          v
simulator.py -> per-machine histories -> model.py (Isolation Forest + baseline deviation)
                                               |
                                               v
                                    agent.py (fact-grounded story)
                                               |
                                owner approves / ignores alert
                                               |
                         notify.py -> technician + dealer simulation
                                               |
                         repair form + worker feedback -> local CSV
                                               |
                                learning labels + impact estimate
```

## Project files

- `app.py`: single-page Streamlit dashboard and workflow
- `simulator.py`: reproducible sensor simulation and fault/dust injection
- `model.py`: per-machine unsupervised model and transparent baseline deviations
- `agent.py`: cautious, evidence-based explanation and repair-slot suggestion
- `notify.py`: language templates, optional gTTS, simulated technician ranking
- `data/`: seeded technicians, dealers, and local repair history

The first 25 normal samples train each model. Feedback labels nudge the demo alert threshold, and repair history informs similar-case wording; this is a lightweight prototype learning loop, not validated predictive maintenance. `data/repair_log.csv` is updated when a repair is saved. Costs, avoided downtime, and savings in the impact panel are user estimates. Optional real CWRU/IMS data is not required for the demo; the app uses simulated data by default.
