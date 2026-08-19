async function loadDashboard() {
  const res = await fetch('../data/latest.json', { cache: 'no-store' });
  const data = await res.json();

  const metrics = [
    ['정규시즌 순위', `${data.summary.rank}위`, data.summary.record],
    ['승률', `${data.summary.win_pct}`, `게임차 ${data.summary.games_back}`],
    ['팀 ERA', `${data.summary.team_era}`, `WHIP ${data.summary.team_whip}`],
    ['팀 AVG', `${data.summary.team_avg}`, `득점 ${data.summary.team_runs} / 안타 ${data.summary.team_hits}`],
    ['탈삼진', `${data.summary.team_so}`, '공식 팀 투수 기록'],
    ['마지막 수집', data.meta.collected_at_utc, 'UTC']
  ];

  document.getElementById('metrics').innerHTML = metrics.map(([label, value, sub]) => `
    <div class="metric">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
      <div class="sub">${sub}</div>
    </div>`).join('');

  document.getElementById('rotationBody').innerHTML = data.rotation.map(p => `
    <tr>
      <td>${p.name}</td>
      <td>${p.era ?? 'null (미수집)'}</td>
      <td>${p.g ?? 'null (미수집)'}</td>
      <td>${p.w == null || p.l == null ? 'null (미수집)' : `${p.w}-${p.l}`}</td>
      <td>${p.ip ?? 'null (미수집)'}</td>
      <td>${p.whip ?? 'null (미수집)'}</td>
      <td>${p.so ?? 'null (미수집)'}</td>
      <td>${p.source ? `<a href="${p.source}" target="_blank" rel="noreferrer">KBO</a>` : 'null (미수집)'}</td>
    </tr>`).join('');

  const latestGame = data.matchups.latest_game ?? 'null (미수집)';
  document.getElementById('matchupBody').innerHTML = `
    <tr><th>NC 전적</th><td>${data.matchups.nc_record ?? 'null (미수집)'}</td></tr>
    <tr><th>최신 경기</th><td>${latestGame}</td></tr>
    <tr><th>팀 순위 출처</th><td><a href="${data.sources.team_rank}" target="_blank" rel="noreferrer">KBO 팀 순위</a></td></tr>
    <tr><th>타격 출처</th><td><a href="${data.sources.team_hitter}" target="_blank" rel="noreferrer">KBO 팀 타자</a></td></tr>
    <tr><th>투수 출처</th><td><a href="${data.sources.team_pitcher}" target="_blank" rel="noreferrer">KBO 팀 투수</a></td></tr>`;

  document.getElementById('meta').textContent = `시즌 ${data.meta.season} · 수집 기준 ${data.meta.collected_at_utc} · ${data.meta.source_note}`;
}

async function refreshNow() {
  if (location.protocol === 'file:') {
    alert('정적 파일 단독 실행에서는 갱신 버튼이 동작하지 않습니다. python app.py 실행 후 localhost 로 접속하세요.');
    return;
  }
  try {
    const res = await fetch('/refresh', { method: 'POST' });
    const payload = await res.json();
    if (!res.ok || !payload.ok) throw new Error(payload.error || 'refresh failed');
    await loadDashboard();
    alert(`갱신 완료: ${payload.collected_at_utc}`);
  } catch (err) {
    alert(`갱신 실패: ${err.message}`);
  }
}

document.getElementById('refreshBtn').addEventListener('click', refreshNow);
loadDashboard().catch(err => {
  document.getElementById('metrics').innerHTML = `<div class="panel fail">대시보드 로드 실패: ${err.message}</div>`;
});
