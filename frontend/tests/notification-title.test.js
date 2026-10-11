import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {notificationTitle} from '../src/notification-title.js';
const session=JSON.parse(readFileSync(new URL('../src/demo/observed-snapshot.json',import.meta.url),'utf8')).approved;
test('notification titles show the virtual-example label exactly once',()=>{
 assert.ok(session.notifications.length>0);
 for(const n of session.notifications){
  const title=notificationTitle(n);
  assert.equal(title.split('가상 예시').length-1,1,title);
  assert.ok(title.includes('모의 발송'));
 }
 assert.equal(notificationTitle({team_name:'팀 A',label:'가상 예시 · 모의 발송'}),'팀 A · 가상 예시 · 모의 발송');
});
