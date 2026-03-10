'use client';
import { useRef } from 'react';
import { QRCodeSVG } from 'qrcode.react';

export default function QRCodeWidget({ value, label }) {
  const qrContainerRef = useRef(null);

  const handlePrint = () => {
    const printWindow = window.open('', '', 'width=600,height=600');
    if (!printWindow) {
      return;
    }

    const doc = printWindow.document;
    doc.title = `${label} - QR Code`;

    const style = doc.createElement('style');
    style.textContent =
      'body { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; }' +
      '.tag { border: 2px solid #000; padding: 20px; text-align: center; border-radius: 10px; }' +
      '.name { font-size: 24px; font-weight: bold; margin-bottom: 10px; }' +
      '.info { font-size: 14px; color: #555; margin-top: 10px; }';
    doc.head.appendChild(style);

    const tag = doc.createElement('div');
    tag.className = 'tag';

    const name = doc.createElement('div');
    name.className = 'name';
    name.textContent = label;

    const qrContainer = doc.createElement('div');
    const sourceSvg = qrContainerRef.current?.querySelector('svg');
    if (sourceSvg) {
      qrContainer.appendChild(sourceSvg.cloneNode(true));
    }

    const info = doc.createElement('div');
    info.className = 'info';
    info.textContent = 'Joolife Smart Farm';

    tag.append(name, qrContainer, info);
    doc.body.appendChild(tag);

    printWindow.addEventListener('load', () => {
      printWindow.print();
      printWindow.close();
    });

    printWindow.setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 120);
  };

  return (
    <div style={{display:"flex", flexDirection:"column", alignItems:"center", gap:"10px"}}>
      <div ref={qrContainerRef} style={{background:"white", padding:"10px", border:"1px solid #EEE", borderRadius:"8px"}}>
        <QRCodeSVG value={value} size={120} />
      </div>
      <button onClick={handlePrint} style={{fontSize:"11px", padding:"4px 8px", background:"#3E2F1C", color:"white", border:"none", borderRadius:"4px", cursor:"pointer"}}>
        🖨️ QR 인쇄
      </button>
    </div>
  );
}
