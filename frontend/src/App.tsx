import { useState } from 'react';
import axios from 'axios';
import { Settings, Printer, Eye, Download } from 'lucide-react';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import './App.css';

interface Config {
  text: string;
  max_line_length: number;
  lines_per_page: number;
  handwriting_consistency: number;
  styles: number;
  ink_color: string;
  pen_thickness: number;
  line_height: number;
  total_lines_per_page: number;
  view_height: number;
  view_width: number;
  margin_left: number;
  margin_top: number;
  page_color: string;
  page_size: string;
  margin_color: string;
  line_color: string;
}

const defaultConfig: Config = {
  text: 'Hello world! This is a test of the automatic handwriting generation tool. I hope it looks realistic and nice!',
  max_line_length: 50,
  lines_per_page: 30,
  handwriting_consistency: 0.98,
  styles: 1,
  ink_color: 'Blue',
  pen_thickness: 0.5,
  line_height: 32,
  total_lines_per_page: 30,
  page_size: 'A5',
  view_height: 210,
  view_width: 148,
  margin_left: 32,
  margin_top: 32,
  page_color: '#FDFDFD',
  margin_color: '#FFCCCC',
  line_color: '#E0E0E0'
};

function App() {
  const [config, setConfig] = useState<Config>(defaultConfig);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [gcodeContent, setGcodeContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [port, setPort] = useState<any>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    let parsedValue: any = value;
    if (type === 'number') {
      parsedValue = parseFloat(value);
    } else if (type === 'range') {
      parsedValue = parseFloat(value);
    }

    if (name === 'page_size') {
      const pageSizes: Record<string, { w: number, h: number }> = {
        'A6': { w: 105, h: 148 },
        'A5': { w: 148, h: 210 },
        'A4': { w: 210, h: 297 },
        'Letter': { w: 215.9, h: 279.4 },
        'Custom': { w: 148, h: 210 }
      };
      const size = pageSizes[value];
      setConfig(prev => ({
        ...prev,
        page_size: value,
        view_width: size.w,
        view_height: size.h
      }));
      return;
    }

    setConfig(prev => ({
      ...prev,
      [name]: parsedValue
    }));
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/generate', config);
      if (response.data && response.data.pages && response.data.pages.length > 0) {
        setSvgContent(response.data.pages[0].svg_content);
        setGcodeContent(response.data.pages[0].gcode_content);
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to generate preview');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = () => fetchData();

  const generatePngFromSvg = (svgString: string): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      const URL = window.URL || window.webkitURL || window;
      const blobURL = URL.createObjectURL(svgBlob);
      
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Canvas context not found'));
          return;
        }
        // Fill white background just in case SVG is transparent
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (blob) resolve(blob);
          else reject(new Error('Blob creation failed'));
          URL.revokeObjectURL(blobURL);
        }, 'image/png');
      };
      img.onerror = (e) => {
        reject(e);
        URL.revokeObjectURL(blobURL);
      };
      img.src = blobURL;
    });
  };

  const handleSave = async () => {
    if (!svgContent || !gcodeContent) {
      setError('No preview generated yet. Please preview first.');
      return;
    }
    const zip = new JSZip();
    zip.file('handwriting.svg', svgContent);
    zip.file('handwriting.gcode', gcodeContent);
    zip.file('source.txt', config.text);
    
    try {
      const pngBlob = await generatePngFromSvg(svgContent);
      zip.file('handwriting.png', pngBlob);
    } catch (e) {
      console.error('Failed to generate PNG', e);
    }

    try {
      const content = await zip.generateAsync({ type: 'blob' });
      saveAs(content, 'handwriting-export.zip');
    } catch (err: any) {
      console.error(err);
      setError('Failed to create ZIP file: ' + err.message);
    }
  };

  const printGCode = async () => {
    if (!gcodeContent) {
      setError('No GCode generated yet. Please generate first.');
      return;
    }

    try {
      // @ts-ignore - Web Serial API might not be typed fully
      const selectedPort = port || await navigator.serial.requestPort();
      
      if (!port) {
        setPort(selectedPort);
      }

      await selectedPort.open({ baudRate: 115200 });
      
      const encoder = new TextEncoderStream();
      const writableStreamClosed = encoder.readable.pipeTo(selectedPort.writable);
      const writer = encoder.writable.getWriter();

      const lines = gcodeContent.split('\n');
      for (const line of lines) {
        if (line.trim()) {
          await writer.write(line + '\n');
          // Add a small delay between lines if needed for standard serial streaming
          await new Promise(r => setTimeout(r, 50));
        }
      }

      writer.close();
      await writableStreamClosed;
      
    } catch (err: any) {
      console.error('Print Error:', err);
      setError('Printing failed: ' + err.message);
    }
  };

  return (
    <div className="app-container">
      {/* Column 1: Configuration */}
      <aside className="sidebar config-column">
        <div className="sidebar-header">
          <Settings size={20} />
          <h2>Configuration</h2>
        </div>

        <div className="config-grid">
          <div className="form-group">
            <label>Consistency</label>
            <div className="consistency-input">
              <input 
                type="range" 
                name="handwriting_consistency" 
                min="0.1" max="1.0" step="0.01" 
                value={config.handwriting_consistency} 
                onChange={handleInputChange} 
              />
              <input 
                type="number"
                name="handwriting_consistency"
                min="0.1" max="1.0" step="0.01"
                value={config.handwriting_consistency}
                onChange={handleInputChange}
                className="number-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Style Seed</label>
            <input type="number" name="styles" value={config.styles} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Max Line Length</label>
            <input type="number" name="max_line_length" value={config.max_line_length} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Total Lines per Page</label>
            <input type="number" name="total_lines_per_page" value={config.total_lines_per_page} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Text Lines per Page</label>
            <input type="number" name="lines_per_page" value={config.lines_per_page} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Pen Thickness</label>
            <input type="number" step="0.1" name="pen_thickness" value={config.pen_thickness} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Line Height</label>
            <input type="number" name="line_height" value={config.line_height} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Page Size</label>
            <select name="page_size" value={config.page_size} onChange={handleInputChange}>
              <option value="A6">A6</option>
              <option value="A5">A5</option>
              <option value="A4">A4</option>
              <option value="Letter">Letter</option>
              <option value="Custom">Custom</option>
            </select>
          </div>

          <div className="form-group">
            <label>Page Width (mm)</label>
            <input type="number" step="0.1" name="view_width" value={config.view_width} onChange={handleInputChange} disabled={config.page_size !== 'Custom'} />
          </div>

          <div className="form-group">
            <label>Page Height (mm)</label>
            <input type="number" step="0.1" name="view_height" value={config.view_height} onChange={handleInputChange} disabled={config.page_size !== 'Custom'} />
          </div>

          <div className="form-group">
            <label>Margin Left</label>
            <input type="number" name="margin_left" value={config.margin_left} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Margin Top</label>
            <input type="number" name="margin_top" value={config.margin_top} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Ink Colour</label>
            <select name="ink_color" value={config.ink_color} onChange={handleInputChange}>
              <option value="Black">Black</option>
              <option value="Blue">Blue</option>
              <option value="Red">Red</option>
              <option value="Green">Green</option>
            </select>
          </div>
        </div>

        <div className="sidebar-footer">
          <button className="btn btn-secondary" onClick={handlePreview} disabled={loading}>
            <Eye size={16} />
            Preview
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={!svgContent || loading}>
            <Download size={16} />
            Save
          </button>
        </div>
      </aside>

      {/* Column 2: Input Text */}
      <aside className="sidebar text-column">
        <div className="sidebar-header">
          <h2>Input Text</h2>
        </div>
        
        <div className="form-group textarea-group">
          <textarea 
            name="text" 
            value={config.text} 
            onChange={handleInputChange} 
            placeholder="Type the text you want to write here..."
          />
        </div>
      </aside>

      {/* Column 3: Main Preview Area */}
      <main className="main-content">
        <header className="main-header">
          <h1>AutoWrite Preview</h1>
          <div className="header-actions">
            <button className="btn btn-secondary" onClick={printGCode} disabled={!gcodeContent}>
              <Printer size={16} />
              Print
            </button>
          </div>
        </header>
        
        {error && <div className="error-message">{error}</div>}

        <div className="preview-pane">
          {svgContent ? (
            <div 
              className="svg-container"
              dangerouslySetInnerHTML={{ __html: svgContent }} 
            />
          ) : (
            <div className="empty-state">
              <p>Click "Preview" or "Generate" to see the handwriting.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
