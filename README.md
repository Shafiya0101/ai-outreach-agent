\---

title: Lab 1 GAN VAE Demo
emoji: 🧵
colorFrom: blue
colorTo: indigo
sdk: gradio
app\_file: app.py
pinned: false
---

# Lab 1 — GAN \& VAE Demo (Fashion-MNIST)

An interactive demo for the models trained in **Lab 1** of the Generative AI labs.
It loads a trained GAN generator and a trained VAE and lets you:

* **GAN samples** — generate fresh images from the GAN generator (with a seed).
* **VAE samples** — sample latent vectors and decode them with the VAE.
* **VAE latent interpolation** — walk between two random latent points and decode each step.

The models are small and run fine on CPU.

## 1\. Export your trained weights (one-time)

The Lab 1 notebook trains the models but doesn't save them. After training `G` and
`vae` in the notebook, add a cell with the contents of `export\\\_weights\\\_snippet.py`
and run it:

```python
import torch
torch.save(G.state\\\_dict(), "gan\\\_generator.pt")
torch.save(vae.state\\\_dict(), "vae.pt")
print("Z\\\_DIM =", Z\\\_DIM, "| LATENT =", LATENT)
```

Download `gan\\\_generator.pt` and `vae.pt` from Colab (Files panel → download) and place
them in this folder, next to `app.py`.

> \\\*\\\*Important:\\\*\\\* make sure `Z\\\_DIM` and `LATENT` printed by the snippet match the values
> at the top of `app.py` (defaults: `Z\\\_DIM = 128`, `LATENT = 32`). If you trained with
> different values, edit `app.py` to match, or the weights won't load.

## 2\. Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open the local URL Gradio prints (usually http://127.0.0.1:7860).

## 3\. Deploy to Hugging Face Spaces (free)

1. Create a new Space at https://huggingface.co/new-space → SDK: **Gradio**.
2. Upload `app.py`, `requirements.txt`, this `README.md`, and your two `.pt` files.
3. The Space builds and launches automatically.

## Files

```
Lab1\\\_App/
├── app.py                     # the Gradio demo
├── requirements.txt
├── export\\\_weights\\\_snippet.py  # paste into the notebook to save weights
├── README.md
├── gan\\\_generator.pt           # <- you add this (from the notebook)
└── vae.pt                     # <- you add this (from the notebook)
```

If the weight files are missing, the app still starts and shows a reminder instead of images.

