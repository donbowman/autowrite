# AutoWrite - Jingan Writing Machine Edition

AutoWrite is a tool that uses Machine Learning to convert typed text into
realistic handwriting. It introduces customizable degrees of randomness
and variations to make it all believable. This version is specifically
optimised to work with [Jingan writing machines](https://jgxzj.com/)
and generates true **single-stroke** centerlines so your pen plotter
draws natural letters without outlining them!

The application uses a **FastAPI backend** and a **React frontend**.

![](screenshot.avif)

## Features
- **True Single-Stroke Output:** Generates authentic single-line paths (both in SVG and G-Code formats) perfect for pen plotters.
- **Modern Web Interface:** A user-friendly React frontend to customize your text, choose from 12 predefined styles, and adjust layouts.
- **FastAPI Backend:** A robust and fast Python backend powering the Recurrent Neural Network (RNN) handwriting synthesis.
- **Smart Formatting:** Automatically splits large texts into lines and pages.
- **Realistic Handwriting:** Powered by a Recurrent Neural Network (RNN) based on Alex Graves' sequence generation architecture.

## Architecture

- **Backend:** Python, FastAPI, TensorFlow (Keras), Uvicorn, Poetry.
- **Frontend:** TypeScript, React, Vite, Tailwind CSS.

---

## How to Run locally

### 1. Using Docker Compose (Recommended)

The easiest way to run the entire application (frontend and backend) is using Docker Compose.

```bash
docker-compose up --build
```

- The **Frontend** will be available at: http://localhost:5000
- The **Backend API** will be available at: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs

### 2. Running Manually (Without Docker)

#### Backend (FastAPI)

Ensure you have Python 3.12+ and Poetry installed.

```bash
# Install dependencies
poetry install

# Set environment variable for TensorFlow/Keras
export TF_USE_LEGACY_KERAS=1

# Run the FastAPI server
poetry run uvicorn autowrite.main:app --host 0.0.0.0 --port 8000
```

#### Frontend (React / Vite)

Ensure you have Node.js (v20+) and npm installed.

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will usually start on http://localhost:5173.

---

## Direct Printing Setup (Jingan Machine)

To send instructions directly to your Jingan writing machine over Bluetooth, you must map your machine to a serial port before running the application.

1. Find your machine's Bluetooth MAC address.
2. Bind it to `/dev/rfcomm0` using the `rfcomm` command:

```bash
sudo rfcomm connect /dev/rfcomm0 28:05:A5:2E:9C:52
```
*(Replace `28:05:A5:2E:9C:52` with the actual MAC address of your machine)*

Once connected, you can use the application to trace your text!

## Output Formats
AutoWrite automatically generates three types of files for every page of text:
- `.gcode` - Raw machine commands (115200 baud, absolute positioning, units in mm)
- `.svg` - Scalable Vector Graphics featuring a precise 1px stroke-width centerline.
- `.png` - Rasterized preview image of the handwriting.

## Acknowledgements

This project is inspired by the work in [handwriting-synthesis](https://github.com/sjvasquez/handwriting-synthesis) which provides the foundational implementation for handwriting synthesis using Recurrent Neural Networks (RNNs).

The handwriting synthesis in AutoWrite is based on the work presented in the paper [Generating Sequences with Recurrent Neural Networks](https://arxiv.org/abs/1308.0850).
