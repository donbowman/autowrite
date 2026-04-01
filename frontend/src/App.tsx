import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Settings, Printer, Eye, Download, X, Activity } from 'lucide-react';
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
  margin_right: number;
  margin_top: number;
  margin_bottom: number;
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
  margin_left: 10,
  margin_right: 10,
  margin_top: 10,
  margin_bottom: 10,
  page_color: '#FDFDFD',
  margin_color: '#FFCCCC',
  line_color: '#E0E0E0'
};

function App() {
  const [config, setConfig] = useState<Config>(() => {
    const saved = localStorage.getItem('autowrite-config');
    if (saved) {
      try {
        return { ...defaultConfig, ...JSON.parse(saved) };
      } catch (e) {
        return defaultConfig;
      }
    }
    return defaultConfig;
  });

  useEffect(() => {
    localStorage.setItem('autowrite-config', JSON.stringify(config));
  }, [config]);

  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [gcodeContent, setGcodeContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [port, setPort] = useState<any>(null);
  const [isPrinting, setIsPrinting] = useState(false);
  const [machineStatus, setMachineStatus] = useState<string | null>(null);
  const [printLogs, setPrintLogs] = useState<{type: 'sent' | 'received' | 'info' | 'error', text: string}[]>([]);
  const [printProgress, setPrintProgress] = useState(0);
  const [showPrintModal, setShowPrintModal] = useState(false);
  const cancelPrintRef = useRef(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const addLog = (type: 'sent' | 'received' | 'info' | 'error', text: string) => {
    setPrintLogs(prev => [...prev, { type, text }]);
    setTimeout(() => {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

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

    setIsPrinting(true);
    setShowPrintModal(true);
    setPrintLogs([]);
    setPrintProgress(0);
    cancelPrintRef.current = false;

    try {
      // @ts-ignore - Web Serial API might not be typed fully
      let selectedPort = port;
      
      if (!selectedPort) {
        // @ts-ignore
        selectedPort = await navigator.serial.requestPort();
        setPort(selectedPort);
      }

      try {
        await selectedPort.open({ baudRate: 115200 });
      } catch (e: any) {
        if (e.name !== 'InvalidStateError' && !e.message?.includes('already open')) {
          console.warn("Error opening port, trying to re-select", e);
          try {
             await selectedPort.close();
          } catch (err) {}
          // Re-select
          // @ts-ignore
          selectedPort = await navigator.serial.requestPort();
          setPort(selectedPort);
          await selectedPort.open({ baudRate: 115200 });
        }
      }
      
      const encoder = new TextEncoderStream();
      const writableStreamClosed = encoder.readable.pipeTo(selectedPort.writable);
      const writer = encoder.writable.getWriter();

      const decoder = new TextDecoderStream();
      const readableStreamClosed = selectedPort.readable.pipeTo(decoder.writable);
      const reader = decoder.readable.getReader();

      const lines = gcodeContent.split('\n').filter(l => l.trim() !== '');
      const totalLines = lines.length;

      let resultBuffer = '';

      try {
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (cancelPrintRef.current) {
            addLog('info', 'Printing cancelled.');
            break;
          }
          
          await writer.write(line + '\n');
          addLog('sent', line);
          
          let response = '';
          while (true) {
             const { value, done } = await reader.read();
             if (done) break;
             if (value) {
                resultBuffer += value;
                if (resultBuffer.includes('\n')) {
                   const parts = resultBuffer.split('\n');
                   for (let j = 0; j < parts.length - 1; j++) {
                     response += parts[j] + '\n';
                   }
                   resultBuffer = parts[parts.length - 1];
                   
                   if (response.toLowerCase().includes('ok') || response.toLowerCase().includes('error')) {
                     break;
                   }
                }
             }
          }
          
          addLog(response.toLowerCase().includes('error') ? 'error' : 'received', response.trim());
          setPrintProgress(Math.round(((i + 1) / totalLines) * 100));
        }
        if (!cancelPrintRef.current) {
          addLog('info', 'Print complete.');
        }
      } finally {
        writer.close();
        await writableStreamClosed;
        reader.cancel();
        reader.releaseLock();
        await readableStreamClosed.catch(() => {});
        await selectedPort.close();
      }
      
    } catch (err: any) {
      console.error('Print Error:', err);
      addLog('error', 'Printing failed: ' + err.message);
    } finally {
      setIsPrinting(false);
    }
  };

  const cancelPrint = () => {
    cancelPrintRef.current = true;
  };

  const checkStatus = async () => {
    try {
      // @ts-ignore
      let selectedPort = port;
      
      if (!selectedPort) {
        // @ts-ignore
        selectedPort = await navigator.serial.requestPort();
        setPort(selectedPort);
      }

      try {
        await selectedPort.open({ baudRate: 115200 });
      } catch (e: any) {
        // Ignore if already open
        if (e.name !== 'InvalidStateError' && !e.message?.includes('already open')) {
          console.warn("Error opening port, trying to re-select", e);
          try {
             await selectedPort.close();
          } catch (err) {}
          // @ts-ignore
          selectedPort = await navigator.serial.requestPort();
          setPort(selectedPort);
          await selectedPort.open({ baudRate: 115200 });
        }
      }
      
      const encoder = new TextEncoderStream();
      const writableStreamClosed = encoder.readable.pipeTo(selectedPort.writable);
      const writer = encoder.writable.getWriter();

      await writer.write('?\n');
      writer.close();
      await writableStreamClosed;

      const decoder = new TextDecoderStream();
      const readableStreamClosed = selectedPort.readable.pipeTo(decoder.writable);
      const reader = decoder.readable.getReader();

      let result = '';
      try {
        // Read the result for a short amount of time
        const timeoutId = setTimeout(() => {
          reader.cancel();
        }, 1000);

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }
          if (value) {
            result += value;
            if (result.includes('>')) {
              reader.cancel();
              clearTimeout(timeoutId);
              break;
            }
          }
        }
      } catch (error) {
        console.error('Error reading status:', error);
      } finally {
        reader.releaseLock();
        await readableStreamClosed.catch(() => {});
        await selectedPort.close();
      }

      setMachineStatus(result.trim() || 'No response');
    } catch (err: any) {
      console.error('Status Error:', err);
      setError('Status check failed: ' + err.message);
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
            <label>Left Margin</label>
            <input type="number" name="margin_left" value={config.margin_left} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Right Margin</label>
            <input type="number" name="margin_right" value={config.margin_right} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Top Margin</label>
            <input type="number" name="margin_top" value={config.margin_top} onChange={handleInputChange} />
          </div>

          <div className="form-group">
            <label>Bottom Margin</label>
            <input type="number" name="margin_bottom" value={config.margin_bottom} onChange={handleInputChange} />
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

      {/* Main Content Area */}
      <main className="main-content">
        <header className="main-header">
          <h1>AutoWrite Preview</h1>
          <div className="header-actions">
            <button className="btn btn-secondary" onClick={checkStatus}>
              <Activity size={16} />
              Status
            </button>
            {isPrinting ? (
              <button className="btn btn-secondary" onClick={() => setShowPrintModal(true)}>
                <Printer size={16} />
                Show Progress
              </button>
            ) : (
              <button className="btn btn-secondary" onClick={printGCode} disabled={!gcodeContent}>
                <Printer size={16} />
                Print
              </button>
            )}
          </div>
        </header>
        
        {machineStatus && <div className="status-message" style={{ padding: '10px', backgroundColor: '#e8f4f8', color: '#0277bd', marginBottom: '20px', borderRadius: '4px' }}>Machine Status: {machineStatus}</div>}
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

      {/* Print Progress Modal */}
      {showPrintModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="modal-content" style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', width: '600px', maxWidth: '90vw', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ margin: 0 }}>Printing Progress</h2>
              <button onClick={() => setShowPrintModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <div style={{ width: '100%', backgroundColor: '#eee', borderRadius: '4px', height: '12px', overflow: 'hidden' }}>
                <div style={{ width: `${printProgress}%`, backgroundColor: '#007bff', height: '100%', transition: 'width 0.2s' }}></div>
              </div>
              <div style={{ textAlign: 'right', fontSize: '12px', color: '#666', marginTop: '4px' }}>{printProgress}% Complete</div>
            </div>

            <div style={{ flex: 1, backgroundColor: '#1e1e1e', color: '#d4d4d4', padding: '12px', borderRadius: '4px', overflowY: 'auto', maxHeight: '400px', fontFamily: 'monospace', fontSize: '12px', marginBottom: '16px' }}>
              {printLogs.map((log, index) => (
                <div key={index} style={{
                  color: log.type === 'error' ? '#f48771' : 
                         log.type === 'info' ? '#75beff' : 
                         log.type === 'received' ? '#b5cea8' : '#d4d4d4',
                  marginBottom: '2px',
                  wordBreak: 'break-all'
                }}>
                  {log.type === 'sent' && '> '}
                  {log.type === 'received' && '< '}
                  {log.text}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              {isPrinting ? (
                <button className="btn btn-secondary" onClick={cancelPrint} style={{ backgroundColor: '#dc3545', color: 'white', borderColor: '#dc3545' }}>
                  <X size={16} /> Cancel Print
                </button>
              ) : (
                <button className="btn btn-primary" onClick={() => setShowPrintModal(false)}>Close</button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
