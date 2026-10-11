// Team names already carry '가상 예시'; show the label once (E-6).
export function notificationTitle(n){
  const label=n.team_name.includes('가상 예시')?n.label.replace(/^가상 예시 · /,''):n.label;
  return n.team_name+' · '+label;
}
