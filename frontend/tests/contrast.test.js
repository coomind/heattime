import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
// WCAG AA (4.5:1) for text on the colours it is drawn on, read from the design tokens.
const css=readFileSync(new URL('../src/theme.css',import.meta.url),'utf8');
const root=css.slice(css.indexOf(':root{'),css.indexOf('}',css.indexOf(':root{')));
const token=name=>{const m=new RegExp('--'+name+':(#[0-9a-fA-F]{6})').exec(root);assert.ok(m,'missing token '+name);return m[1];};
const lum=hex=>{const c=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(v=>v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4);return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2];};
const ratio=(a,b)=>{const [x,y]=[lum(a),lum(b)].sort((p,q)=>q-p);return (x+0.05)/(y+0.05);};
const pairs=[['ink','bg'],['ink','surface'],['muted','bg'],['muted','surface'],['accent-ink','accent'],['warn-ink','warn-bg'],['ink','warn-bg'],['ink','accent-soft'],
 ['st0-ink','st0-bg'],['st1-ink','st1-bg'],['st2-ink','st2-bg'],['st3-ink','st3-bg'],['st4-ink','st4-bg'],['accent','surface']];
for(const [fg,bg] of pairs)test(`${fg} on ${bg} meets 4.5:1`,()=>{const r=ratio(token(fg),token(bg));assert.ok(r>=4.5,`${fg}/${bg} = ${r.toFixed(2)}`);});
