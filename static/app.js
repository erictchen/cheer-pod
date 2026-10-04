/**
 * CheerPod — Frontend Client Logic
 * Lightweight, uncluttered cheer stunt group generator & roster database.
 */

// Application State
let squadAthletes = [];
let checkedMap = {}; // { [id]: boolean }
let activeRoleFilter = 'ALL';
let athleteSearchTerm = '';
let currentSkillMode = 'balanced'; // 'balanced' or 'stacked'
let generatedPods = [];
let generatedUnassigned = [];
let swapContext = null; // { podId, role, athlete }

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initApp();
  setupHeightInputs();
});

async function initApp() {
  await fetchAthletes();
}

/**
 * Fetch athletes from SQLite backend
 */
async function fetchAthletes() {
  try {
    const res = await fetch('/api/athletes');
    const data = await res.json();
    if (data.success && data.athletes) {
      squadAthletes = data.athletes;
      
      // Default: Check all active athletes if not already set
      squadAthletes.forEach(a => {
        if (checkedMap[a.id] === undefined) {
          checkedMap[a.id] = (a.is_active === 1);
        }
      });

      renderChecklist();
      renderRosterTable();
      updateAttendanceSummary();
      updateReadiness();
    }
  } catch (err) {
    console.error('Error fetching athletes:', err);
  }
}

/**
 * Tab Switching
 */
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  if (tabId === 'generator') {
    document.getElementById('tabGeneratorBtn').classList.add('active');
    document.getElementById('generatorView').classList.add('active');
  } else if (tabId === 'roster') {
    document.getElementById('tabRosterBtn').classList.add('active');
    document.getElementById('rosterView').classList.add('active');
    renderRosterTable();
  }
}

/**
 * Format height inches into feet and inches (e.g. 64 -> 5'4")
 */
function formatHeight(inches) {
  if (!inches) return '--';
  const ft = Math.floor(inches / 12);
  const rem = inches % 12;
  const remStr = Number.isInteger(rem) ? rem : rem.toFixed(1);
  return `${ft}'${remStr}"`;
}

/**
 * Render stars for skill rating (1-5)
 */
function renderStars(level) {
  const stars = '★'.repeat(level) + '☆'.repeat(5 - level);
  return `<span class="skill-stars" title="Skill level: ${level}/5">${stars}</span>`;
}

/**
 * Role badge helper
 */
function getRoleBadge(role) {
  const roleClass = 'role-' + role.replace(/\s+/g, '');
  return `<span class="role-badge-sm ${roleClass}">${role}</span>`;
}

/**
 * Attendance Checklist rendering
 */
function renderChecklist() {
  const container = document.getElementById('athletesCheckGrid');
  if (!container) return;

  const filtered = squadAthletes.filter(a => {
    // Role filter
    if (activeRoleFilter !== 'ALL') {
      const pRole = a.primary_role.toLowerCase();
      const target = activeRoleFilter.toLowerCase();
      if (target === 'base') {
        if (!pRole.includes('base')) return false;
      } else if (!pRole.includes(target)) {
        return false;
      }
    }
    // Search query
    if (athleteSearchTerm.trim()) {
      const term = athleteSearchTerm.toLowerCase();
      const nameMatch = a.name.toLowerCase().includes(term);
      const roleMatch = a.primary_role.toLowerCase().includes(term);
      if (!nameMatch && !roleMatch) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
        No athletes found matching filters.
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(a => {
    const isChecked = !!checkedMap[a.id];
    const initials = a.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    const secTag = a.secondary_roles
      ? `<span class="flex-role-tag" title="Flex: ${escapeHtml(a.secondary_roles)}">Flex: ${escapeHtml(a.secondary_roles)}</span>`
      : '';

    return `
      <div class="athlete-check-card ${isChecked ? 'checked' : ''}" onclick="toggleCheck(${a.id}, event)">
        <input type="checkbox" class="athlete-checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleCheck(${a.id})">
        <div class="athlete-avatar">${initials}</div>
        <div class="athlete-info">
          <div class="athlete-name-row">
            <span class="athlete-name" title="${escapeHtml(a.name)}">${escapeHtml(a.name)}</span>
            ${getRoleBadge(a.primary_role)}
          </div>
          <div class="athlete-details-row">
            <span class="height-tag">${formatHeight(a.height_inches)} <small>(${a.height_inches}")</small></span>
            ${renderStars(a.skill_level)}
            ${secTag}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Toggle an athlete's attendance check
 */
function toggleCheck(athleteId, event) {
  if (event && event.target && event.target.tagName === 'INPUT') {
    // Already handled by checkbox input
    checkedMap[athleteId] = event.target.checked;
  } else {
    checkedMap[athleteId] = !checkedMap[athleteId];
  }
  renderChecklist();
  updateAttendanceSummary();
  updateReadiness();
}

/**
 * Select All / Clear All
 */
function selectAll(checked) {
  squadAthletes.forEach(a => {
    checkedMap[a.id] = checked;
  });
  renderChecklist();
  updateAttendanceSummary();
  updateReadiness();
}

/**
 * Filter handlers
 */
function setRoleFilter(role) {
  activeRoleFilter = role;
  document.querySelectorAll('.chip-filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.role === role);
  });
  renderChecklist();
}

function filterAthletes() {
  athleteSearchTerm = document.getElementById('athleteSearch').value;
  renderChecklist();
}

/**
 * Update attendance stats & readiness prediction
 */
function updateAttendanceSummary() {
  const activeAthletes = squadAthletes.filter(a => checkedMap[a.id]);
  const total = squadAthletes.length;
  const count = activeAthletes.length;

  document.getElementById('checkedCount').textContent = count;
  document.getElementById('totalCount').textContent = `/ ${total}`;
  document.getElementById('rosterCountBadge').textContent = total;

  let flyers = 0, bases = 0, backs = 0, fronts = 0;
  activeAthletes.forEach(a => {
    const r = a.primary_role.toLowerCase();
    if (r.includes('flyer')) flyers++;
    else if (r.includes('base')) bases++;
    else if (r.includes('backspot')) backs++;
    else if (r.includes('front')) fronts++;
  });

  document.getElementById('countFlyer').textContent = flyers;
  document.getElementById('countBase').textContent = bases;
  document.getElementById('countBackspot').textContent = backs;
  document.getElementById('countFront').textContent = fronts;
}

/**
 * Dynamic calculation of readiness & coaching feedback
 */
function updateReadiness() {
  const active = squadAthletes.filter(a => checkedMap[a.id]);
  const n = active.length;
  const badge = document.getElementById('podReadinessBadge');
  const text = document.getElementById('podReadinessText');

  if (n === 0) {
    badge.className = 'pod-readiness-badge';
    text.textContent = 'Check off athletes to begin';
    return;
  }

  let flyers = 0, bases = 0, backs = 0;
  active.forEach(a => {
    const r = a.primary_role.toLowerCase();
    if (r.includes('flyer')) flyers++;
    else if (r.includes('base')) bases++;
    else if (r.includes('backspot')) backs++;
  });

  const fullPodsPossible = Math.min(flyers, Math.floor(bases / 2), backs);
  
  if (fullPodsPossible > 0) {
    badge.className = 'pod-readiness-badge';
    badge.style.background = '#ecfdf5';
    badge.style.color = '#047857';
    badge.style.borderColor = '#a7f3d0';
    text.innerHTML = `Ready to build <b>${fullPodsPossible} Full Pods</b> (4-person)`;
  } else if (flyers === 0) {
    badge.style.background = '#fffbeb';
    badge.style.color = '#b45309';
    badge.style.borderColor = '#fde68a';
    text.textContent = 'Need at least 1 Flyer checked in';
  } else if (bases < 2) {
    badge.style.background = '#fffbeb';
    badge.style.color = '#b45309';
    badge.style.borderColor = '#fde68a';
    text.textContent = `Need at least 2 Bases (currently ${bases})`;
  } else if (backs < 1) {
    badge.style.background = '#fffbeb';
    badge.style.color = '#b45309';
    badge.style.borderColor = '#fde68a';
    text.textContent = 'Need at least 1 Backspot checked in';
  } else {
    badge.className = 'pod-readiness-badge';
    text.textContent = `${n} athletes selected`;
  }
}

/**
 * Skill Mode Toggle
 */
function setMode(mode) {
  currentSkillMode = mode;
  document.querySelectorAll('#modeControl .segment-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
}

/**
 * Generate Stunt Groups from Server
 */
async function generateGroups() {
  const activeIds = squadAthletes.filter(a => checkedMap[a.id]).map(a => a.id);
  const sizeStrategy = document.getElementById('sizeSelect').value;

  if (activeIds.length < 2) {
    alert('Please check off at least 2 athletes who are present.');
    return;
  }

  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Optimizing Pods...</span>`;

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        athlete_ids: activeIds,
        mode: currentSkillMode,
        size_strategy: sizeStrategy
      })
    });

    const data = await res.json();
    if (data.success) {
      generatedPods = data.pods || [];
      generatedUnassigned = data.unassigned || [];
      renderGeneratedPods(data);
    } else {
      alert('Error generating groups: ' + (data.error || 'Unknown error'));
    }
  } catch (err) {
    console.error('Failed to generate stunt groups:', err);
    alert('Failed to connect to generator server.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span class="btn-sparkle">✨</span><span>Generate Stunt Groups</span>`;
  }
}

/**
 * Render Generated Stunt Pods
 */
function renderGeneratedPods(data) {
  const pods = data.pods || [];
  const unassigned = data.unassigned || [];
  const container = document.getElementById('podsContainer');
  const adviceBox = document.getElementById('coachAdviceBox');
  const actionsBar = document.getElementById('resultsActions');
  const subtitle = document.getElementById('resultsSubtitle');

  actionsBar.style.display = 'flex';
  subtitle.textContent = `${pods.length} stunt groups generated for ${data.total_active} athletes`;

  // Coach Advice / Notes
  if (data.coach_advice && data.coach_advice.length > 0) {
    adviceBox.style.display = 'block';
    adviceBox.innerHTML = `💡 <b>Coach Tip:</b> ${data.coach_advice.join(' ')}`;
  } else {
    adviceBox.style.display = 'none';
  }

  if (pods.length === 0) {
    container.innerHTML = `
      <div class="results-placeholder">
        <div class="placeholder-icon">⚠️</div>
        <h3>No valid stunt pods could be formed</h3>
        <p>${escapeHtml(data.message || 'Please check more athletes or adjust pod sizing.')}</p>
      </div>`;
    return;
  }

  container.innerHTML = pods.map(pod => renderPodCard(pod)).join('');

  // Unassigned / Bench Section
  const unassignedBox = document.getElementById('unassignedContainer');
  const unassignedGrid = document.getElementById('unassignedGrid');
  const unassignedBadge = document.getElementById('unassignedCountBadge');

  if (unassigned.length > 0) {
    unassignedBox.style.display = 'block';
    unassignedBadge.textContent = unassigned.length;
    unassignedGrid.innerHTML = unassigned.map(a => `
      <div class="unassigned-card">
        <div>
          <b style="font-size: 0.9rem;">${escapeHtml(a.name)}</b>
          <div style="display: flex; gap: 0.4rem; align-items: center; margin-top: 0.15rem;">
            ${getRoleBadge(a.primary_role)}
          </div>
        </div>
        <button class="btn btn-ghost btn-xs" onclick="openSwapModalForBench(${a.id})" title="Swap into a pod">Swap In</button>
      </div>
    `).join('');
  } else {
    unassignedBox.style.display = 'none';
  }
}

/**
 * Render a Single Pod Card
 */
function renderPodCard(pod) {
  const flyer = pod.flyer;
  const mainBase = pod.main_base;
  const sideBase = pod.side_base;
  const backspot = pod.backspot;
  const frontSpot = pod.front_spot;

  const athletes = [flyer, mainBase, sideBase, backspot, frontSpot].filter(Boolean);

  return `
    <div class="pod-card" id="podCard-${pod.id}">
      <div class="pod-card-header">
        <div class="pod-title-group">
          <span class="pod-title">Pod ${pod.id}</span>
          <span class="pod-count-badge">${athletes.length} Athletes</span>
        </div>
      </div>

      <!-- Formation Diagram Layout -->
      <div class="pod-formation">
        <!-- 1. Flyer Slot (Top) -->
        ${renderFormationSlot(pod.id, 'flyer', 'Flyer', flyer, 'slot-flyer')}

        <!-- 2. Bases (Main Base, Side Base) -->
        <div class="bases-pair-row">
          ${renderFormationSlot(pod.id, 'main_base', 'Main Base', mainBase, 'slot-main')}
          ${renderFormationSlot(pod.id, 'side_base', 'Side Base', sideBase, 'slot-side')}
        </div>

        <!-- 3. Backspot Slot (Bottom) -->
        ${renderFormationSlot(pod.id, 'backspot', 'Backspot', backspot, 'slot-back')}

        <!-- 4. Front Spot Slot (If present) -->
        ${frontSpot ? renderFormationSlot(pod.id, 'front_spot', 'Front Spot', frontSpot, 'slot-front') : ''}
      </div>
    </div>
  `;
}

/**
 * Render an individual formation role slot inside a pod card
 */
function renderFormationSlot(podId, roleKey, roleTitle, athlete, slotClass) {
  if (!athlete) {
    return `
      <div class="formation-slot ${slotClass}" style="opacity: 0.6; border-style: dashed;">
        <div class="slot-left">
          <span class="slot-role-tag">${roleTitle}</span>
          <span class="slot-athlete-name" style="color: var(--text-muted); font-style: italic;">Unfilled</span>
        </div>
      </div>`;
  }

  return `
    <div class="formation-slot ${slotClass}">
      <div class="slot-left">
        <span class="slot-role-tag">${roleTitle}</span>
        <span class="slot-athlete-name" title="${escapeHtml(athlete.name)}">${escapeHtml(athlete.name)}</span>
      </div>
      <div class="slot-right">
        <button class="btn-swap-slot" onclick="openSwapModal(${podId}, '${roleKey}', ${athlete.id})" title="Swap ${escapeHtml(athlete.name)} with another athlete">
          ⇄
        </button>
      </div>
    </div>
  `;
}

/**
 * Interactive Swap Functionality
 */
function openSwapModal(podId, roleKey, athleteId) {
  const currentAthlete = squadAthletes.find(a => a.id === athleteId);
  if (!currentAthlete) return;

  swapContext = { podId, roleKey, athlete: currentAthlete };
  
  const modal = document.getElementById('swapModal');
  const prompt = document.getElementById('swapModalPrompt');
  const list = document.getElementById('swapCandidatesList');

  prompt.innerHTML = `Swap <b>${escapeHtml(currentAthlete.name)}</b> (${currentAthlete.primary_role}) with:`;

  // Candidates: all other checked athletes
  const candidates = squadAthletes.filter(a => checkedMap[a.id] && a.id !== athleteId);

  list.innerHTML = candidates.map(c => `
    <div class="swap-candidate-item" onclick="executeSwap(${c.id})">
      <div>
        <b style="font-size: 0.92rem;">${escapeHtml(c.name)}</b>
        <div style="display: flex; gap: 0.4rem; align-items: center; margin-top: 0.15rem;">
          ${getRoleBadge(c.primary_role)}
        </div>
      </div>
      <span class="btn btn-ghost btn-xs">Swap In →</span>
    </div>
  `).join('');

  modal.showModal();
}

function openSwapModalForBench(benchAthleteId) {
  const benchAth = squadAthletes.find(a => a.id === benchAthleteId);
  if (!benchAth) return;

  // Swap target: pick who to replace from generated pods
  const modal = document.getElementById('swapModal');
  const prompt = document.getElementById('swapModalPrompt');
  const list = document.getElementById('swapCandidatesList');

  prompt.innerHTML = `Swap <b>${escapeHtml(benchAth.name)}</b> from Bench into a pod. Replace who?`;

  const placedAthletes = [];
  generatedPods.forEach(p => {
    ['flyer', 'main_base', 'side_base', 'backspot', 'front_spot'].forEach(role => {
      if (p[role]) {
        placedAthletes.push({ podId: p.id, roleKey: role, athlete: p[role] });
      }
    });
  });

  list.innerHTML = placedAthletes.map(item => `
    <div class="swap-candidate-item" onclick="executeBenchSwap(${item.podId}, '${item.roleKey}', ${benchAth.id})">
      <div>
        <b style="font-size: 0.92rem;">${escapeHtml(item.athlete.name)}</b> (Pod ${item.podId})
        <div style="display: flex; gap: 0.4rem; align-items: center; margin-top: 0.2rem;">
          ${getRoleBadge(item.athlete.primary_role)}
        </div>
      </div>
      <span class="btn btn-ghost btn-xs">Replace</span>
    </div>
  `).join('');

  modal.showModal();
}

function executeBenchSwap(podId, roleKey, benchAthId) {
  const pod = generatedPods.find(p => p.id === podId);
  const benchAth = squadAthletes.find(a => a.id === benchAthId);
  if (!pod || !benchAth) return;

  const oldAth = pod[roleKey];
  pod[roleKey] = benchAth;

  // Move oldAth to unassigned
  generatedUnassigned = generatedUnassigned.filter(a => a.id !== benchAthId);
  if (oldAth) {
    generatedUnassigned.push(oldAth);
  }

  closeSwapModal();
  recalculateAndRerender();
}

function executeSwap(targetAthleteId) {
  if (!swapContext) return;
  const { podId, roleKey, athlete: sourceAth } = swapContext;
  const targetAth = squadAthletes.find(a => a.id === targetAthleteId);
  if (!targetAth) return;

  const sourcePod = generatedPods.find(p => p.id === podId);
  if (!sourcePod) return;

  // Check where targetAth is currently
  let targetLocation = null;
  generatedPods.forEach(p => {
    ['flyer', 'main_base', 'side_base', 'backspot', 'front_spot'].forEach(rk => {
      if (p[rk] && p[rk].id === targetAthleteId) {
        targetLocation = { pod: p, roleKey: rk };
      }
    });
  });

  if (targetLocation) {
    // Both are in pods -> swap them
    targetLocation.pod[targetLocation.roleKey] = sourceAth;
    sourcePod[roleKey] = targetAth;
  } else {
    // Target was unassigned on bench
    sourcePod[roleKey] = targetAth;
    generatedUnassigned = generatedUnassigned.filter(a => a.id !== targetAthleteId);
    generatedUnassigned.push(sourceAth);
  }

  closeSwapModal();
  recalculateAndRerender();
}

function recalculateAndRerender() {
  // Recalculate metrics for all pods
  generatedPods.forEach(pod => {
    const mems = [pod.flyer, pod.main_base, pod.side_base, pod.backspot, pod.front_spot].filter(Boolean);
    const avgSkill = mems.length ? (mems.reduce((sum, a) => sum + a.skill_level, 0) / mems.length).toFixed(1) : 0;
    
    let baseDiff = null;
    let baseRating = 'N/A';
    let maxBaseH = 0;
    if (pod.main_base && pod.side_base) {
      baseDiff = Math.abs(pod.main_base.height_inches - pod.side_base.height_inches).toFixed(1);
      baseRating = baseDiff <= 0.5 ? 'Perfect Match' : (baseDiff <= 1.2 ? 'Good Match' : 'Noticeable');
      maxBaseH = Math.max(pod.main_base.height_inches, pod.side_base.height_inches);
    } else if (pod.main_base) {
      maxBaseH = pod.main_base.height_inches;
      baseRating = 'Single Base';
    } else if (pod.side_base) {
      maxBaseH = pod.side_base.height_inches;
      baseRating = 'Single Base';
    }

    let backClearance = null;
    let backRating = 'N/A';
    if (pod.backspot && maxBaseH > 0) {
      backClearance = (pod.backspot.height_inches - maxBaseH).toFixed(1);
      backRating = backClearance >= 1.0 ? 'Optimal Reach' : (backClearance >= 0 ? 'Level Reach' : 'Shorter than Base');
    }

    pod.metrics = {
      avg_skill: avgSkill,
      base_diff: baseDiff,
      base_rating: baseRating,
      backspot_clearance: backClearance,
      backspot_rating: backRating
    };
  });

  renderGeneratedPods({
    pods: generatedPods,
    unassigned: generatedUnassigned,
    total_active: squadAthletes.filter(a => checkedMap[a.id]).length,
    mode: currentSkillMode
  });
}

function closeSwapModal() {
  const modal = document.getElementById('swapModal');
  modal.close();
  swapContext = null;
}

/**
 * Copy Pods to Clipboard for Text/Messaging
 */
function copyPodsToClipboard() {
  if (generatedPods.length === 0) return;

  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  let text = `📣 CHEER STUNT GROUPS — ${dateStr}\n`;
  text += `=====================================\n\n`;

  generatedPods.forEach(p => {
    text += `POD ${p.id}:\n`;
    if (p.flyer) text += `  • Flyer: ${p.flyer.name}\n`;
    if (p.main_base) text += `  • Main Base: ${p.main_base.name}\n`;
    if (p.side_base) text += `  • Side Base: ${p.side_base.name}\n`;
    if (p.backspot) text += `  • Backspot: ${p.backspot.name}\n`;
    if (p.front_spot) text += `  • Front Spot: ${p.front_spot.name}\n`;
    text += `\n`;
  });

  if (generatedUnassigned.length > 0) {
    text += `BENCH / ALTERNATES:\n`;
    generatedUnassigned.forEach(a => {
      text += `  • ${a.name} (${a.primary_role})\n`;
    });
  }

  navigator.clipboard.writeText(text).then(() => {
    alert('✅ Stunt groups copied to clipboard! Ready to paste into your team chat.');
  }).catch(err => {
    console.error('Clipboard copy failed:', err);
    prompt('Copy the roster text below:', text);
  });
}

/**
 * ROSTER DATABASE FUNCTIONS
 */
function renderRosterTable() {
  const tbody = document.getElementById('rosterTableBody');
  const countLabel = document.getElementById('rosterTotalLabel');
  if (!tbody) return;

  const term = (document.getElementById('rosterSearch')?.value || '').toLowerCase().trim();
  const list = squadAthletes.filter(a => {
    if (!term) return true;
    return a.name.toLowerCase().includes(term) ||
           a.primary_role.toLowerCase().includes(term) ||
           (a.notes && a.notes.toLowerCase().includes(term));
  });

  countLabel.textContent = `${list.length} Athletes on File`;

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No athletes found.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(a => `
    <tr>
      <td>
        <b>${escapeHtml(a.name)}</b>
      </td>
      <td>${getRoleBadge(a.primary_role)}</td>
      <td>${a.secondary_roles ? escapeHtml(a.secondary_roles) : '<span style="color:var(--text-light);">—</span>'}</td>
      <td>
        <span class="height-tag">${formatHeight(a.height_inches)}</span>
        <small style="color:var(--text-light); margin-left: 0.2rem;">(${a.height_inches}")</small>
      </td>
      <td>${renderStars(a.skill_level)}</td>
      <td>
        <span class="badge" style="${a.is_active ? 'background:#ecfdf5; color:#047857;' : 'background:#fef2f2; color:#dc2626;'}">
          ${a.is_active ? 'Active' : 'Injured/Inactive'}
        </span>
      </td>
      <td style="max-width: 200px; font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(a.notes || '')}">
        ${escapeHtml(a.notes || '—')}
      </td>
      <td style="text-align: right; white-space: nowrap;">
        <button class="btn btn-ghost btn-xs" onclick="openEditAthleteModal(${a.id})">Edit</button>
        <button class="btn-danger-ghost btn-xs" onclick="deleteAthlete(${a.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

function filterRosterTable() {
  renderRosterTable();
}

/**
 * Add / Edit Athlete Modal Handling
 */
function setupHeightInputs() {
  const ftIn = document.getElementById('athHeightFeet');
  const inIn = document.getElementById('athHeightInches');
  const help = document.getElementById('totalHeightHelp');

  function update() {
    const feet = parseFloat(ftIn.value) || 0;
    const inches = parseFloat(inIn.value) || 0;
    const total = (feet * 12) + inches;
    if (help) help.textContent = `Total: ${total.toFixed(1)} inches (${feet}'${inches}")`;
  }

  if (ftIn && inIn) {
    ftIn.addEventListener('input', update);
    inIn.addEventListener('input', update);
  }
}

function openAddAthleteModal() {
  document.getElementById('modalTitle').textContent = 'Add Athlete to Roster';
  document.getElementById('editAthleteId').value = '';
  document.getElementById('athleteForm').reset();
  document.getElementById('athHeightFeet').value = '5';
  document.getElementById('athHeightInches').value = '4';
  document.getElementById('athSkillLevel').value = '3';
  document.getElementById('athIsActive').checked = true;
  document.getElementById('totalHeightHelp').textContent = 'Total: 64.0 inches';
  document.getElementById('athleteModal').showModal();
}

function openEditAthleteModal(athleteId) {
  const a = squadAthletes.find(x => x.id === athleteId);
  if (!a) return;

  document.getElementById('modalTitle').textContent = 'Edit Athlete Details';
  document.getElementById('editAthleteId').value = a.id;
  document.getElementById('athName').value = a.name;
  document.getElementById('athPrimaryRole').value = a.primary_role;
  document.getElementById('athSecondaryRoles').value = a.secondary_roles || '';
  
  const ft = Math.floor(a.height_inches / 12);
  const rem = a.height_inches % 12;
  document.getElementById('athHeightFeet').value = ft;
  document.getElementById('athHeightInches').value = rem;
  document.getElementById('totalHeightHelp').textContent = `Total: ${a.height_inches} inches (${ft}'${rem}")`;

  document.getElementById('athSkillLevel').value = a.skill_level;
  document.getElementById('athIsActive').checked = (a.is_active === 1);
  document.getElementById('athNotes').value = a.notes || '';

  document.getElementById('athleteModal').showModal();
}

function closeAthleteModal() {
  document.getElementById('athleteModal').close();
}

async function handleAthleteSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('editAthleteId').value;
  const feet = parseFloat(document.getElementById('athHeightFeet').value) || 5;
  const inches = parseFloat(document.getElementById('athHeightInches').value) || 0;
  const totalInches = (feet * 12) + inches;

  const payload = {
    name: document.getElementById('athName').value.trim(),
    primary_role: document.getElementById('athPrimaryRole').value,
    secondary_roles: document.getElementById('athSecondaryRoles').value.trim(),
    height_inches: totalInches,
    skill_level: parseInt(document.getElementById('athSkillLevel').value, 10),
    is_active: document.getElementById('athIsActive').checked ? 1 : 0,
    notes: document.getElementById('athNotes').value.trim()
  };

  try {
    let res;
    if (id) {
      // Update
      res = await fetch(`/api/athletes/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      // Create
      res = await fetch('/api/athletes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }

    const data = await res.json();
    if (data.success) {
      closeAthleteModal();
      await fetchAthletes();
    } else {
      alert('Error saving athlete: ' + (data.error || 'Unknown error'));
    }
  } catch (err) {
    console.error('Failed to save athlete:', err);
    alert('Failed to connect to database.');
  }
}

async function deleteAthlete(athleteId) {
  const a = squadAthletes.find(x => x.id === athleteId);
  if (!a) return;
  if (!confirm(`Are you sure you want to remove ${a.name} from the team roster?`)) return;

  try {
    const res = await fetch(`/api/athletes/${athleteId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      delete checkedMap[athleteId];
      await fetchAthletes();
    }
  } catch (err) {
    console.error('Delete athlete error:', err);
  }
}

/**
 * Reset Demo Squad Data
 */
async function resetDemoData() {
  if (!confirm('Reset the database to the 20 preloaded realistic cheer demo athletes?')) return;
  try {
    const res = await fetch('/api/reset-demo', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      checkedMap = {};
      await fetchAthletes();
      document.getElementById('podsContainer').innerHTML = `
        <div class="results-placeholder">
          <div class="placeholder-icon">🤸‍♂️</div>
          <h3>Demo Squad Reset!</h3>
          <p>Check off the present athletes on the left, then click <strong>Generate Stunt Groups</strong>.</p>
        </div>`;
      document.getElementById('unassignedContainer').style.display = 'none';
      document.getElementById('resultsActions').style.display = 'none';
      alert('Demo cheer team refreshed successfully!');
    }
  } catch (err) {
    console.error('Reset error:', err);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * QR Code Modal for Phone & iPad
 */
function openQrModal() {
  const modal = document.getElementById('qrModal');
  if (modal) modal.showModal();
}

function closeQrModal() {
  const modal = document.getElementById('qrModal');
  if (modal) modal.close();
}

function copyNetworkUrl() {
  const url = document.getElementById('qrUrlLabel')?.textContent?.trim() || 'http://192.168.0.13:8000';
  navigator.clipboard.writeText(url).then(() => {
    alert('✅ Link copied to clipboard:\n' + url);
  }).catch(() => {
    prompt('Copy URL:', url);
  });
}

