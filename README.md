# AutoWrite - Jingan Writing Machine Edition

AutoWrite is a tool that uses Machine Learning to convert typed text into
realistic handwriting. It introduces customizable degrees of randomness
and variations to make it all believable. This version is specifically
optimised to work with [Jingan writing machines](https://jgxzj.com/)
and generates true **single-stroke** centerlines so your pen plotter
draws natural letters without outlining them!

Run with
`poetry run autowrite`

after poetry install.

![](screenshot.avif)

### Features
- **True Single-Stroke Output:** Generates authentic single-line paths (both in SVG and G-Code formats) perfect for pen plotters.
- **Direct Serial Printing:** Send G-Code directly to your Jingan writing machine over Bluetooth.
- **Customisation:** Choose from 12 predefined styles and adjust line spacing, page size, margins, and layout directly from a user-friendly GUI.
- **Smart Formatting:** Automatically splits large texts into lines and pages.
- **Realistic Handwriting:** Powered by a Recurrent Neural Network (RNN) based on Alex Graves' sequence generation architecture.

### Direct Printing Setup (Jingan Machine)

To use the **PRINT** feature in the GUI to send instructions directly
to your Jingan writing machine over Bluetooth, you must map your machine
to a serial port before running the application.

1. Find your machine's Bluetooth MAC address.
2. Bind it to `/dev/rfcomm0` using the `rfcomm` command:

```bash
sudo rfcomm connect /dev/rfcomm0 28:05:A5:2E:9C:52
```
*(Replace `28:05:A5:2E:9C:52` with the actual MAC address of your machine)*

Once connected, you can use the **PRINT** button in the AutoWrite GUI to trace your text!

### Output Formats
AutoWrite automatically generates three types of files for every page of text:
- `.gcode` - Raw machine commands (115200 baud, absolute positioning, units in mm)
- `.svg` - Scalable Vector Graphics featuring a precise 1px stroke-width centerline.
- `.png` - Rasterized preview image of the handwriting.

### Acknowledgements

This project is inspired by the work in
[handwriting-synthesis](https://github.com/sjvasquez/handwriting-synthesis)
which provides the foundational implementation for handwriting synthesis
using Recurrent Neural Networks (RNNs).

The handwriting synthesis in AutoWrite is based on the work
presented in the paper [Generating Sequences with Recurrent Neural Networks](https://arxiv.org/abs/1308.0850).
