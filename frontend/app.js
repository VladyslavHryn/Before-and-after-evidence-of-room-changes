const state = {
    beforeFiles: [],
    afterFiles: []
};

// ── DOM refs ─────────────────────────────────────────────────────────────────
const analyzeBtn     = document.getElementById('analyze-btn');
const loadDemoBtn    = document.getElementById('load-demo-btn');
const beforeZone     = document.getElementById('drop-zone-before');
const afterZone      = document.getElementById('drop-zone-after');
const beforeInput    = document.getElementById('file-input-before');
const afterInput     = document.getElementById('file-input-after');
const previewBefore  = document.getElementById('preview-before');
const previewAfter   = document.getElementById('preview-after');
const clearBefore    = document.getElementById('clear-before');
const clearAfter     = document.getElementById('clear-after');

// ── Demo logic ───────────────────────────────────────────────────────────────
loadDemoBtn.addEventListener('click', async () => {
    loadDemoBtn.disabled = true;
    loadDemoBtn.textContent = 'Loading...';
    try {
        const fetchFile = async (url, filename) => {
            const res = await fetch(url);
            const blob = await res.blob();
            return new File([blob], filename, { type: 'image/png' });
        };
        const bFile = await fetchFile('/test_sets/set1/before1.png', 'before1.png');
        const aFile = await fetchFile('/test_sets/set1/after1.png', 'after1.png');
        
        state.beforeFiles = [bFile];
        state.afterFiles = [aFile];
        
        renderPreviews(state.beforeFiles, previewBefore, 'before');
        renderPreviews(state.afterFiles, previewAfter, 'after');
        updateAnalyzeButton();
    } catch (err) {
        console.error('Failed to load demo images:', err);
        alert('Could not load demo images. Make sure test_sets is generated.');
    } finally {
        loadDemoBtn.textContent = 'Load Demo Data';
        loadDemoBtn.disabled = false;
    }
});

// ── Upload zones ─────────────────────────────────────────────────────────────
function setupUploadZone(zone, input, type) {
    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('active');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('active');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('active');
        handleFiles(e.dataTransfer.files, type);
    });

    input.addEventListener('change', (e) => {
        handleFiles(e.target.files, type);
        e.target.value = '';  // allow re-selecting the same file
    });
}

function handleFiles(files, type) {
    const validFiles = Array.from(files).filter(f => f.type.startsWith('image/'));

    if (type === 'before') {
        state.beforeFiles = [...state.beforeFiles, ...validFiles].slice(0, 3);
        renderPreviews(state.beforeFiles, previewBefore, 'before');
    } else {
        state.afterFiles = [...state.afterFiles, ...validFiles].slice(0, 3);
        renderPreviews(state.afterFiles, previewAfter, 'after');
    }

    updateAnalyzeButton();
}

function renderPreviews(files, container, type) {
    container.innerHTML = '';
    files.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const div = document.createElement('div');
            div.className = 'thumbnail';
            div.innerHTML = `
                <img src="${e.target.result}" alt="preview">
                <button class="remove-btn" onclick="removeFile('${type}', ${index})">&times;</button>
            `;
            container.appendChild(div);
        };
        reader.readAsDataURL(file);
    });
}

window.removeFile = (type, index) => {
    if (type === 'before') {
        state.beforeFiles.splice(index, 1);
        renderPreviews(state.beforeFiles, previewBefore, 'before');
    } else {
        state.afterFiles.splice(index, 1);
        renderPreviews(state.afterFiles, previewAfter, 'after');
    }
    updateAnalyzeButton();
};

clearBefore.addEventListener('click', () => {
    state.beforeFiles = [];
    renderPreviews([], previewBefore, 'before');
    updateAnalyzeButton();
});

clearAfter.addEventListener('click', () => {
    state.afterFiles = [];
    renderPreviews([], previewAfter, 'after');
    updateAnalyzeButton();
});

function updateAnalyzeButton() {
    const isValid =
        state.beforeFiles.length > 0 &&
        state.afterFiles.length > 0;
    analyzeBtn.disabled = !isValid;
}

setupUploadZone(beforeZone, beforeInput, 'before');
setupUploadZone(afterZone, afterInput, 'after');
updateAnalyzeButton();

// ── Analyze ──────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
    const loading        = document.getElementById('loading');
    const results        = document.getElementById('results');
    const errorContainer = document.getElementById('error-container');

    loading.classList.remove('hidden');
    results.classList.add('hidden');
    errorContainer.classList.add('hidden');
    analyzeBtn.disabled = true;

    const formData = new FormData();
    state.beforeFiles.forEach(f => formData.append('before_images', f));
    state.afterFiles.forEach(f => formData.append('after_images', f));

    const startTime = Date.now();

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(`Server error ${response.status}: ${errBody}`);
        }

        const data = await response.json();
        data._clientTimeMs = Date.now() - startTime;

        renderResults(data);
        loading.classList.add('hidden');
        results.classList.remove('hidden');
    } catch (err) {
        loading.classList.add('hidden');
        errorContainer.textContent = err.message || 'An error occurred during analysis.';
        errorContainer.classList.remove('hidden');
    } finally {
        updateAnalyzeButton();  // re-enable if inputs are still valid
    }
});

// ── Rendering ────────────────────────────────────────────────────────────────

function renderResults(data) {
    /*
     * Backend response shape (from AnalysisResult.model_dump()):
     *   scene: { lighting_change, viewpoint_change, coverage_comparison }
     *   confirmed_changes: [ { name, bbox_before, bbox_after, status, confidence, evidence_note } ]
     *   unchanged_objects: [ ... same ... ]
     *   uncertain_matches: [ { object_name, reason, suggested_action, bbox_before } ]
     *   processing_time_seconds: float
     *   token_usage: { prompt_tokens, completion_tokens, total_tokens }
     *   estimated_cost_usd: float
     *   warnings: [str]
     *   evidence_crops: { "object name": { before?: base64, after?: base64 } }
     */
    renderMetrics(data);
    renderSceneAssessment(data.scene || {});
    renderConfirmedChanges(data.confirmed_changes || [], data.evidence_crops || {});
    renderUncertainMatches(data.uncertain_matches || [], data.evidence_crops || {});
    renderUnchangedObjects(data.unchanged_objects || []);
    renderWarnings(data.warnings || []);
}

// ── Badges ───────────────────────────────────────────────────────────────────

function statusBadge(status) {
    const map = {
        added:            'badge-green',
        removed:          'badge-red',
        moved:            'badge-yellow',
        not_verifiable:   'badge-blue',
        unchanged:        'badge-gray',
    };
    const cls = map[status] || 'badge-blue';
    const label = (status || '').replace(/_/g, ' ').toUpperCase();
    return `<span class="badge ${cls}">${label}</span>`;
}

function confidenceBadge(confidence) {
    // confidence is a string: "high" | "medium" | "low"
    const map = { high: 'badge-green', medium: 'badge-yellow', low: 'badge-red' };
    const cls = map[confidence] || 'badge-blue';
    return `<span class="badge ${cls}" style="margin-left:0.5rem">${(confidence || '').toUpperCase()}</span>`;
}

// ── Metrics ──────────────────────────────────────────────────────────────────

function renderMetrics(data) {
    const bar = document.getElementById('metrics-bar');
    const serverTime = (data.processing_time_seconds || 0).toFixed(1);
    const clientTime = data._clientTimeMs ? (data._clientTimeMs / 1000).toFixed(1) : serverTime;
    const tokens = data.token_usage ? data.token_usage.total_tokens : 0;
    const cost = data.estimated_cost_usd || 0;

    bar.innerHTML = `
        <div><strong>Server time:</strong> ${serverTime}s</div>
        <div><strong>Round-trip:</strong> ${clientTime}s</div>
        <div><strong>Tokens:</strong> ${tokens.toLocaleString()}</div>
        <div><strong>Est. cost:</strong> $${cost.toFixed(4)}</div>
    `;
}

// ── Scene Assessment ─────────────────────────────────────────────────────────

function renderSceneAssessment(scene) {
    const el = document.getElementById('scene-content');
    el.innerHTML = `
        <p><strong>Lighting Change:</strong> ${scene.lighting_change || 'N/A'}</p>
        <p><strong>Viewpoint Change:</strong> ${scene.viewpoint_change || 'N/A'}</p>
        <p><strong>Coverage Comparison:</strong> ${scene.coverage_comparison || 'N/A'}</p>
    `;
}

// ── Confirmed Changes ────────────────────────────────────────────────────────

function renderConfirmedChanges(changes, evidenceCrops) {
    const container = document.getElementById('confirmed-changes-list');
    container.innerHTML = '';

    if (changes.length === 0) {
        container.innerHTML = '<p class="card" style="text-align:center;color:var(--text-muted)">No confirmed physical changes detected.</p>';
        return;
    }

    changes.forEach(change => {
        const div = document.createElement('div');
        div.className = 'card';

        // Evidence crops keyed by object name
        let evidenceHtml = '';
        const crops = evidenceCrops[change.name];
        if (crops) {
            evidenceHtml = `
                <div class="evidence-grid">
                    <div class="evidence-col">
                        <strong>Before</strong>
                        ${crops.before
                            ? `<img class="evidence-img" src="data:image/png;base64,${crops.before}" alt="Before evidence">`
                            : '<p class="text-muted">No crop available</p>'}
                    </div>
                    <div class="evidence-col">
                        <strong>After</strong>
                        ${crops.after
                            ? `<img class="evidence-img" src="data:image/png;base64,${crops.after}" alt="After evidence">`
                            : '<p class="text-muted">No crop available</p>'}
                    </div>
                </div>
            `;
        }

        div.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:0.5rem">
                <h4>${escapeHtml(change.name)}</h4>
                <div>
                    ${statusBadge(change.status)}
                    ${confidenceBadge(change.confidence)}
                </div>
            </div>
            <p><strong>Evidence:</strong> ${escapeHtml(change.evidence_note || '')}</p>
            ${evidenceHtml}
        `;
        container.appendChild(div);
    });
}

// ── Uncertain Matches ────────────────────────────────────────────────────────

function renderUncertainMatches(matches, evidenceCrops) {
    const section   = document.getElementById('uncertain-matches-section');
    const container = document.getElementById('uncertain-matches-list');
    container.innerHTML = '';

    if (!matches || matches.length === 0) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    matches.forEach(match => {
        const div = document.createElement('div');
        div.className = 'card';

        // Show before-crop if available
        let cropHtml = '';
        const crops = evidenceCrops[match.object_name];
        if (crops && crops.before) {
            cropHtml = `
                <div style="margin-top:1rem">
                    <strong>Last known position (Before):</strong>
                    <img class="evidence-img" src="data:image/png;base64,${crops.before}" alt="Before location" style="max-width:300px;margin-top:0.5rem;display:block">
                </div>
            `;
        }

        div.innerHTML = `
            <h4>${escapeHtml(match.object_name)} ${statusBadge('not_verifiable')}</h4>
            <p><strong>Reason:</strong> ${escapeHtml(match.reason || '')}</p>
            <p><strong>Suggested action:</strong> ${escapeHtml(match.suggested_action || '')}</p>
            ${cropHtml}
        `;
        container.appendChild(div);
    });
}

// ── Unchanged Objects ────────────────────────────────────────────────────────

function renderUnchangedObjects(objects) {
    const container = document.getElementById('unchanged-objects-list');
    container.innerHTML = '';

    if (!objects || objects.length === 0) {
        container.innerHTML = '<p style="padding-top:1rem">None detected.</p>';
        return;
    }

    const ul = document.createElement('ul');
    ul.style.paddingTop = '1rem';
    ul.style.paddingLeft = '1.5rem';
    objects.forEach(obj => {
        const li = document.createElement('li');
        // obj is a DetectedObject with .name and .evidence_note
        li.textContent = typeof obj === 'string' ? obj : (obj.name || 'Unknown');
        if (obj.evidence_note) {
            const small = document.createElement('small');
            small.style.color = 'var(--text-muted)';
            small.style.marginLeft = '0.5rem';
            small.textContent = `— ${obj.evidence_note}`;
            li.appendChild(small);
        }
        ul.appendChild(li);
    });
    container.appendChild(ul);
}

// ── Warnings ─────────────────────────────────────────────────────────────────

function renderWarnings(warnings) {
    const container = document.getElementById('error-container');
    if (!warnings || warnings.length === 0) return;

    // Show warnings as a non-blocking note (not hiding results)
    const warningDiv = document.createElement('div');
    warningDiv.className = 'alert';
    warningDiv.style.backgroundColor = '#fef3c7';
    warningDiv.style.color = '#92400e';
    warningDiv.style.border = '1px solid #d97706';
    warningDiv.innerHTML = `<strong>Warnings:</strong><ul>${warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>`;

    const results = document.getElementById('results');
    results.insertBefore(warningDiv, results.firstChild.nextSibling);
}

// ── Utility ──────────────────────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
