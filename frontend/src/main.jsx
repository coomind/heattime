import React from 'react';import {createRoot} from 'react-dom/client';import App from './App.jsx';import './fonts/fonts.css';import '@fontsource/ibm-plex-mono/latin-500.css';import './styles.css';import './theme.css';// Disclosure buttons: every <details><summary> reports its state with aria-expanded (styled as a button in theme.css).
const syncSummary=d=>{const s=d.querySelector(':scope>summary');if(s)s.setAttribute('aria-expanded',String(d.open));};
document.addEventListener('toggle',e=>{if(e.target instanceof HTMLDetailsElement)syncSummary(e.target);},true);
new MutationObserver(()=>document.querySelectorAll('details').forEach(syncSummary)).observe(document.body,{childList:true,subtree:true});
createRoot(document.getElementById('root')).render(<App/>);