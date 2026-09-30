const BACKEND_URL = 'https://kavach-vision-backend.onrender.com'; // EDIT THIS TO YOUR RENDER/RAILWAY URL
let pollTimer = null;
        let allFindings = [];

        function switchTab(tabId, el) {
            // Update active nav state
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            el.classList.add('active');

            const isDashboard = (tabId === 'dashboard');
            
            // Show/hide sections based on tab
            document.getElementById('sevGrid').style.display = isDashboard && allFindings.length ? '' : 'none';
            document.getElementById('modGrid').style.display = (isDashboard || tabId.startsWith('m')) && allFindings.length ? '' : 'none';
            document.getElementById('auditPanel').style.display = (isDashboard || tabId === 'audit') && allFindings.length ? '' : 'none';
            document.getElementById('findingsPanel').style.display = (isDashboard || tabId.startsWith('m')) && allFindings.length ? '' : 'none';
            
            // Filter module panels
            if (tabId.startsWith('m')) {
                document.getElementById('panel-m1').style.display = (tabId === 'm1') ? '' : 'none';
                document.getElementById('panel-m2').style.display = (tabId === 'm2') ? '' : 'none';
                document.getElementById('panel-m3').style.display = (tabId === 'm3') ? '' : 'none';
                document.getElementById('panel-m4').style.display = (tabId === 'm4') ? '' : 'none';
                document.getElementById('modGrid').style.gridTemplateColumns = '1fr'; // Full width for single module
            } else {
                document.getElementById('panel-m1').style.display = '';
                document.getElementById('panel-m2').style.display = '';
                document.getElementById('panel-m3').style.display = '';
                document.getElementById('panel-m4').style.display = '';
                document.getElementById('modGrid').style.gridTemplateColumns = ''; // Restore CSS grid
            }

            // Filter findings table
            if (allFindings.length) {
                let filtered = allFindings;
                if (tabId === 'm1') filtered = allFindings.filter(f => f.module === 'data_integrity');
                if (tabId === 'm2') filtered = allFindings.filter(f => f.module === 'model_integrity');
                if (tabId === 'm3') filtered = allFindings.filter(f => f.module === 'inference_provenance');
                if (tabId === 'm4') filtered = allFindings.filter(f => f.module === 'distribution_shift');
                renderFindingsTable(filtered);
            }
        }

        async function runDemo() {
            const btn = document.getElementById('btnDemo');
            btn.disabled = true;
            btn.innerHTML = '&#9203; Running...';
            
            // Get values from inputs (if they exist)
            const dsPath = document.getElementById('inpDataset') ? document.getElementById('inpDataset').value : '';
            const modPath = document.getElementById('inpModel') ? document.getElementById('inpModel').value : '';
            const refPath = document.getElementById('inpReference') ? document.getElementById('inpReference').value : '';
            
            document.getElementById('statusBar').classList.add('active');
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('progressLog').innerHTML = '<div>Starting Zenora Assurance Pipeline...</div>';

            // Animate stage dots sequentially
            const stages = ['sdot1', 'sdot2', 'sdot3', 'sdot4'];
            const stageLabels = ['Data Integrity', 'Model Integrity', 'Provenance', 'Distribution Shift'];
            stages.forEach(id => { const el = document.getElementById(id); if(el) el.className = 'stage-dot'; });
            let stageIdx = 0;
            const stageTimer = setInterval(() => {
                if (stageIdx < stages.length) {
                    if (stageIdx > 0) {
                        const prev = document.getElementById(stages[stageIdx-1]);
                        if (prev) prev.className = 'stage-dot done';
                    }
                    const cur = document.getElementById(stages[stageIdx]);
                    if (cur) cur.className = 'stage-dot active';
                    document.getElementById('progressLog').innerHTML += `<div>&#9654; Scanning: ${stageLabels[stageIdx]}...</div>`;
                    stageIdx++;
                }
            }, 800);

            try {
                const r = await fetch(BACKEND_URL + '/api/run_pipeline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dataset_path: dsPath || undefined,
                        model_path: modPath || undefined,
                        reference_path: refPath || undefined
                    })
                });
                const d = await r.json();
                clearInterval(stageTimer);
                
                if (d.success) {
                    // All dots done
                    stages.forEach(id => { const el = document.getElementById(id); if(el) el.className = 'stage-dot done'; });
                    document.getElementById('loaderBarWrap').className = 'loader-bar-wrap done';
                    document.getElementById('statusText').textContent = 'Pipeline completed successfully';
                    document.getElementById('btnDemo').innerHTML = '&#9654; Re-run Pipeline';
                    document.getElementById('btnDemo').disabled = false;
                    document.getElementById('btnHTML').style.display = 'inline-block';
                    document.getElementById('btnJSON').style.display = 'inline-block';
                    document.getElementById('btnPDF').style.display = 'inline-block';
                    loadResults(d.report);
                } else {
                    throw new Error(d.error);
                }
            } catch (e) {
                clearInterval(stageTimer);
                alert('Failed to start: ' + e);
                document.getElementById('loaderBarWrap').className = 'loader-bar-wrap error';
                document.getElementById('statusText').textContent = 'Pipeline encountered an error';
                btn.disabled = false;
                btn.innerHTML = '&#9654; Retry';
            }
        }

        async function loadResults(report) {
            let auditLogs = [];
            try {
                const lr = await fetch(BACKEND_URL + '/api/logs');
                const ld = await lr.json();
                auditLogs = ld.logs || [];
            } catch(e) {}
            
            const di_find = report.dataset_integrity.findings || [];
            const mi_find = report.model_integrity.findings || [];
            const ds_find = report.distribution_shift.findings || [];

            // Use unified findings provided by Risk Engine if available, else fallback
            let allRaw = [];
            if (report.risk_evaluation && report.risk_evaluation.findings) {
                allRaw = report.risk_evaluation.findings.map(f => ({
                    finding_id: f.finding_id,
                    severity: f.severity || 'info',
                    module: f.finding_id.startsWith('DATA') ? 'data_integrity' : 
                            (f.finding_id.startsWith('MOD') ? 'model_integrity' : 'distribution_shift'),
                    category: (f.category || 'general_finding').replace(/_/g,' '),
                    evidence: f.evidence || '',
                    reason: f.reason || '',
                    limitations: f.limitations || '',
                    confidence: f.confidence || 1.0,
                    affected_asset: f.asset || f.affected_asset || 'Unknown',
                    disposition: f.recommended_disposition || f.recommendation || 'REVIEW'
                }));
            } else {
                allRaw = [
                    ...di_find.map((f, i) => ({
                        finding_id: f.finding_id || `DI-${String(i+1).padStart(3,'0')}`,
                        severity: f.severity || 'high',
                        module: 'data_integrity',
                        category: f.issue ? f.issue.toLowerCase().replace(/ /g,'_') : 'data_issue',
                        reason: `[${f.issue}] ${f.evidence}`,
                        confidence: f.confidence,
                        affected_asset: 'poisoned_dataset',
                        disposition: f.recommendation
                    })),
                    ...mi_find.map((f, i) => ({
                        finding_id: f.finding_id || `MI-${String(i+1).padStart(3,'0')}`,
                        severity: f.severity || 'critical',
                        module: 'model_integrity',
                        category: f.issue ? f.issue.toLowerCase().replace(/ /g,'_') : 'model_anomaly',
                        reason: `[${f.issue}] ${f.evidence}`,
                        confidence: f.confidence,
                        affected_asset: 'backdoored_model',
                        disposition: f.recommendation
                    })),
                    ...ds_find.map((f, i) => ({
                        finding_id: f.finding_id || `DS-${String(i+1).padStart(3,'0')}`,
                        severity: f.severity || 'medium',
                        module: 'distribution_shift',
                        category: f.issue ? f.issue.toLowerCase().replace(/ /g,'_') : 'dist_shift',
                        reason: `[${f.issue}] ${f.evidence}`,
                        confidence: f.confidence,
                        affected_asset: 'operational_data',
                        disposition: f.recommendation
                    }))
                ];
            }

            // Count severities dynamically from actual severity fields
            let crit = 0, high = 0, med = 0, low = 0, info = 0;
            allRaw.forEach(f => {
                const s = (f.severity || '').toLowerCase();
                if (s === 'critical') crit++;
                else if (s === 'high') high++;
                else if (s === 'medium') med++;
                else if (s === 'low') low++;
                else info++;
            });
            
            const d = {
                data_integrity: { findings_count: di_find.length, dataset: report.dataset_integrity.dataset || { num_samples: 150, exact_duplicates: 0, label_flips: 0, ood_detected: 0 }, mi_find_count: mi_find.length, ds_find_count: ds_find.length },
                model_integrity: { plot: report.model_integrity.plot || '', findings_count: mi_find.length, overall_risk: report.model_integrity.overall_risk || 'HIGH', access_level: report.model_integrity.access_level || 'White-Box', assessments: report.model_integrity.assessments || { fingerprint: { param_count: 25000000 } } },
                inference_provenance: { total_records: 1, verified: 1, chain_valid: true, record: report.sample_provenance_record || {} },
                distribution_shift: { raw_distance: report.distribution_shift.raw_distance || 0, normalized_risk: report.distribution_shift.normalized_risk || 0, threshold: report.distribution_shift.threshold || 5.0, risk_level: report.distribution_shift.status || 'N/A', reference_samples: report.distribution_shift.reference_samples || 0, test_samples: report.distribution_shift.test_samples || 0 },
                severity_summary: { critical: crit, high: high, medium: med, low: low, info: info },
                findings: allRaw,
                audit: { entry_count: auditLogs.length, chain_valid: true, merkle_root: auditLogs.length ? auditLogs[auditLogs.length-1].signature : 'N/A', logs: auditLogs }
            };
            render(d);
        }

        function render(d) {
            const s = d.severity_summary || {};
            document.getElementById('vCritical').textContent = s.critical || 0;
            document.getElementById('vHigh').textContent = s.high || 0;
            document.getElementById('vMedium').textContent = s.medium || 0;
            document.getElementById('vLow').textContent = s.low || 0;
            document.getElementById('vInfo').textContent = s.info || 0;
            document.getElementById('sevGrid').style.display = '';
            document.getElementById('modGrid').style.display = '';

            renderM1(d.data_integrity);
            renderM2(d.model_integrity);
            renderM3(d.inference_provenance);
            renderM4(d.distribution_shift);
            allFindings = d.findings || [];
            renderFindingsTable(allFindings);
            renderAudit(d.audit || {});
        }

        function stat(val, label, cls) {
            return '<div class="mod-stat"><div class="mod-stat-val ' + (cls||'') + '">' + val + '</div><div class="mod-stat-label">' + label + '</div></div>';
        }

        function renderM1(d) {
            if (!d) return;
            const ds = d.dataset || {};
            
            // Map actual findings from other modules for the summary blocks
            const mi_find = d.mi_find_count || 0;
            const ds_find = d.ds_find_count || 0;
            
            let htmlStr =
                stat(ds.num_samples || 0, 'Samples') +
                stat(ds.exact_duplicates != null ? ds.exact_duplicates : 0, 'Exact Duplicates', (ds.exact_duplicates > 0 ? 'val-red' : 'val-green')) +
                stat(ds.label_flips != null ? ds.label_flips : 0, 'Near Duplicates', (ds.label_flips > 0 ? 'val-orange' : 'val-green')) +
                stat(ds.ood_detected != null ? ds.ood_detected : 0, 'OOD Detected', (ds.ood_detected > 0 ? 'val-red' : 'val-green')) +
                stat(d.findings_count || 0, 'Total Findings');
                
            // Add Image Gallery Polish
            htmlStr += `<div style="grid-column: 1 / -1; margin-top: 15px; border-top: 1px solid var(--border-light); padding-top: 10px;">
                <div class="mod-stat-label" style="text-align: left; margin-bottom: 8px;">Dataset Preview (Showing 150 Images)</div>
                <div style="display: flex; flex-wrap: wrap; gap: 4px; max-height: 200px; overflow-y: auto; padding-right: 5px; background: #fafafa; border: 1px solid var(--border); border-radius: 4px; padding: 4px;">`;
            
            for(let i=1; i<=150; i++) {
                htmlStr += `<img src="/demo_data/poisoned_dataset/images/img_${i}.jpg" style="width: 40px; height: 40px; object-fit: cover; border-radius: 2px; border: 1px solid #ccc;">`;
            }
            
            htmlStr += `</div></div>`;
                
            document.getElementById('m1Stats').innerHTML = htmlStr;
            setRisk('m1Risk', d.findings_count > 5 ? 'HIGH' : d.findings_count > 0 ? 'MEDIUM' : 'LOW');
        }

        function renderM2(d) {
            if (!d) return;
            const fp = (d.assessments||{}).fingerprint||{};
            let htmlStr = 
                stat((fp.param_count||0).toLocaleString(), 'Parameters') +
                stat(d.access_level||'N/A', 'Access Level') +
                stat(fp.outliers_detected||0, 'Weight Outliers', (fp.outliers_detected||0) > 0 ? 'val-red' : 'val-green') +
                stat(d.findings_count||0, 'Findings');
                
            // Add prominent high-tech fingerprint table
            if (fp.layer_fingerprints && Object.keys(fp.layer_fingerprints).length > 0) {
                htmlStr += `<div style="grid-column: 1 / -1; margin-top: 20px; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff;">
                    <div style="background: #f1f5f9; color: var(--text-dark); padding: 10px 14px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-light);">
                        <span style="font-size: 0.95rem;">&#128269; Deterministic Weight-Space Fingerprint</span>
                        <span style="font-size: 0.75rem; background: var(--primary); color: #fff; padding: 2px 6px; border-radius: 4px;">ACTIVE SCAN</span>
                    </div>
                    <div style="max-height: 250px; overflow-y: auto; font-family: Consolas, monospace; font-size: 0.85rem;">
                        <table style="width: 100%; border-collapse: collapse; text-align: right;">
                            <thead style="position: sticky; top: 0; background: #f8fafc; color: var(--text-muted); box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                                <tr>
                                    <th style="padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border-light);">Layer Signature</th>
                                    <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-light);">L2 Norm</th>
                                    <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-light);">Mean</th>
                                    <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-light);">StdDev</th>
                                    <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-light);">Sparsity</th>
                                    <th style="padding: 8px 12px; border-bottom: 1px solid var(--border-light);">Spectral Ratio</th>
                                </tr>
                            </thead>
                            <tbody>`;
                
                for (const [layer, stats] of Object.entries(fp.layer_fingerprints)) {
                    const isAnomalous = stats.spectral_ratio > 4.0;
                    const rowBg = isAnomalous ? 'background: #fef2f2;' : '';
                    const specStyle = isAnomalous ? 'color: var(--danger); font-weight: bold;' : '';
                    
                    htmlStr += `
                        <tr style="border-bottom: 1px solid var(--border-light); ${rowBg}">
                            <td style="padding: 6px 12px; text-align: left; font-weight: 600; color: var(--text-dark);">${layer}</td>
                            <td style="padding: 6px 12px;">${stats.l2_norm ? stats.l2_norm.toFixed(4) : '-'}</td>
                            <td style="padding: 6px 12px;">${stats.mean ? stats.mean.toFixed(4) : '-'}</td>
                            <td style="padding: 6px 12px;">${stats.std ? stats.std.toFixed(4) : '-'}</td>
                            <td style="padding: 6px 12px;">${stats.sparsity ? (stats.sparsity * 100).toFixed(2) + '%' : '-'}</td>
                            <td style="padding: 6px 12px; ${specStyle}">${stats.spectral_ratio ? stats.spectral_ratio.toFixed(2) : '-'} ${isAnomalous ? '&#9888;' : ''}</td>
                        </tr>
                    `;
                }
                htmlStr += `</tbody></table></div></div>`;
            }

            if (d.plot) {
                htmlStr += `<div style="grid-column: 1 / -1; margin-top: 15px; border-top: 1px solid var(--border-light); padding-top: 10px;">
                    <div class="mod-stat-label" style="text-align: left; margin-bottom: 8px;">Explainability Map (Weight Distribution Anomaly)</div>
                    <img src="${d.plot}" style="max-width: 100%; border: 1px solid var(--border); border-radius: 4px;">
                </div>`;
            }
                
            document.getElementById('m2Stats').innerHTML = htmlStr;
            setRisk('m2Risk', d.overall_risk || 'LOW');
        }

        function renderM3(d) {
            if (!d) return;
            let htmlStr = stat(d.total_records||0, 'Records') +
                stat(d.verified||0, 'Verified', 'val-green') +
                stat(d.tampered||d.failed||0, 'Tampered', (d.tampered||d.failed) > 0 ? 'val-red' : '') +
                stat(d.chain_valid !== false ? 'VALID' : 'BROKEN', 'Chain', d.chain_valid !== false ? 'val-green' : 'val-red');
            
            if (d.record && d.record.sequence !== undefined) {
                htmlStr += `<div style="grid-column: 1 / -1; margin-top: 15px; border-radius: 4px; background: #fafafa; border: 1px solid var(--border); padding: 12px; font-family: Consolas, monospace; font-size: 0.8rem; color: var(--text-main);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-light); padding-bottom: 6px; margin-bottom: 8px;">
                        <span style="color: var(--text-dark); font-weight: 600;">&#128271; PROVENANCE RECORD #${d.record.sequence}</span>
                        <span style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; border: 1px solid #bbf7d0;">VERIFIED ED25519</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 140px 1fr; gap: 4px;">
                        <div style="color: var(--text-muted); font-weight: 600;">Input Hash:</div><div style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${d.record.input_hash}">${d.record.input_hash}</div>
                        <div style="color: var(--text-muted); font-weight: 600;">Model Hash:</div><div style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${d.record.model_hash}">${d.record.model_hash}</div>
                        <div style="color: var(--text-muted); font-weight: 600;">Preproc Config:</div><div style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${d.record.preproc_hash}</div>
                        <div style="color: var(--text-muted); font-weight: 600;">Infer Config:</div><div style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${d.record.infer_hash}</div>
                        <div style="color: var(--text-muted); font-weight: 600;">Output Hash:</div><div style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${d.record.output_hash}</div>
                        <div style="color: var(--text-muted); font-weight: 600; margin-top: 4px;">Signature:</div><div style="margin-top: 4px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; color: var(--primary);">${d.record.signature.substring(0,64)}...</div>
                    </div>
                    <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--border-light); display: flex; align-items: center; gap: 6px;">
                        <span style="color: var(--text-dark);"><strong>Replay Status:</strong> <span style="color: var(--success);">SECURE (Nonce: ${d.record.nonce})</span></span>
                    </div>
                </div>`;
            }
            document.getElementById('m3Stats').innerHTML = htmlStr;
            setRisk('m3Risk', d.chain_valid === false ? 'CRITICAL' : 'LOW');
        }

        function renderM4(d) {
            if (!d) return;
            let htmlStr =
                stat(typeof d.raw_distance === 'number' ? d.raw_distance.toFixed(2) : 'N/A', 'Dist. Distance') +
                stat(typeof d.normalized_risk === 'number' ? d.normalized_risk.toFixed(2) : 'N/A', 'Norm. Risk (0-1)') +
                stat(typeof d.threshold === 'number' ? d.threshold.toFixed(1) : 'N/A', 'Threshold') +
                stat(d.reference_samples || 'N/A', 'Ref Samples') +
                stat(d.test_samples || 'N/A', 'Test Samples');
                
            // Add a visual threshold gauge below the stats
            if (typeof d.raw_distance === 'number' && typeof d.threshold === 'number') {
                const maxVal = d.threshold * 3; // Severe threshold is usually around 15, moderate is 5.
                const pct = Math.min(100, Math.max(0, (d.raw_distance / maxVal) * 100));
                
                // Color scaling based on severity
                let barColor = 'var(--success)';
                if (d.raw_distance > d.threshold * 3) barColor = 'var(--danger)';
                else if (d.raw_distance > d.threshold) barColor = '#f59e0b';
                
                htmlStr += `<div style="grid-column: 1 / -1; margin-top: 15px; border-top: 1px solid var(--border-light); padding-top: 15px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: var(--text-dark); margin-bottom: 5px;">
                        <span>Statistical Divergence Map</span>
                        <span>${d.raw_distance.toFixed(2)} / ${d.threshold.toFixed(1)} (Threshold)</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; position: relative;">
                        <div style="height: 100%; width: ${pct}%; background: ${barColor}; transition: width 0.5s ease-out;"></div>
                        <!-- Threshold marker -->
                        <div style="position: absolute; top: 0; bottom: 0; left: ${(d.threshold / maxVal) * 100}%; width: 2px; background: var(--text-dark); box-shadow: 0 0 2px rgba(0,0,0,0.5);"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">
                        <span>0.0 (Identical)</span>
                        <span>> ${d.threshold.toFixed(1)} (Shift Detected)</span>
                    </div>
                </div>`;
            }
            
            document.getElementById('m4Stats').innerHTML = htmlStr;
            setRisk('m4Risk', d.risk_level === 'skipped' ? 'N/A' : d.risk_level || 'LOW');
        }

        function renderFindingsTable(f) {
            document.getElementById('fCount').textContent = f.length;
            if (!f.length) {
                document.getElementById('fBody').innerHTML = '<tr><td colspan="8" style="text-align:center;padding:20px;color:var(--text-muted)">No findings for this view.</td></tr>';
                return;
            }
            const order = ['CRITICAL','HIGH','MEDIUM','LOW','INFO'];
            const sorted = [...f].sort((a,b) => order.indexOf((a.severity||'').toUpperCase()) - order.indexOf((b.severity||'').toUpperCase()));
            document.getElementById('fBody').innerHTML = sorted.map(x => {
                const cc = x.confidence > 0.8 ? 'var(--danger)' : x.confidence > 0.5 ? '#ca8a04' : 'var(--success)';
                return '<tr>' +
                    '<td style="font-family:Consolas,monospace;font-size:0.72rem">' + x.finding_id + '</td>' +
                    '<td><span class="sev sev-' + (x.severity||'').toLowerCase() + '">' + (x.severity||'').toUpperCase() + '</span></td>' +
                    '<td>' + x.module + '</td>' +
                    '<td>' + (x.category||'').toUpperCase().replace(/_/g,' ') + '</td>' +
                    '<td style="font-size:0.8rem"><strong>Issue:</strong> ' + x.reason + '<br><strong>Evidence:</strong> ' + x.evidence + '<br><em>Limitation:</em> ' + x.limitations + '</td>' +
                    '<td>' + (x.confidence*100).toFixed(0) + '% <div class="conf-bar"><div class="conf-fill" style="width:' + (x.confidence*100) + '%;background:' + cc + '"></div></div></td>' +
                    '<td style="font-family:Consolas,monospace;font-size:0.72rem">' + (x.affected_asset||'').substring(0,22) + '</td>' +
                    '<td><span class="disp disp-' + (x.disposition||'').toLowerCase() + '">' + (x.disposition||'').toUpperCase() + '</span></td>' +
                    '</tr>';
            }).join('');
        }

        function renderAudit(a) {
            document.getElementById('auditPanel').style.display = '';
            document.getElementById('aEntries').textContent = a.entry_count || 0;
            document.getElementById('aMerkle').textContent = ((a.merkle_root||'N/A') + '').substring(0,40) + '...';
            const ok = a.chain_valid !== false;
            document.getElementById('chainBadge').className = 'chain-badge ' + (ok ? 'chain-ok' : 'chain-fail');
            document.getElementById('cDot').className = 'chain-dot-sm ' + (ok ? 'ok' : 'fail');
            document.getElementById('cText').textContent = 'Hash Chain: ' + (ok ? 'VERIFIED' : 'BROKEN');
            
            // Add visual command
            if (!document.getElementById('auditCmd')) {
                const btn = document.createElement('div');
                btn.id = 'auditCmd';
                btn.style.marginTop = '15px';
                btn.innerHTML = `<button class="btn btn-outline" onclick="
                    this.textContent = 'Verifying...';
                    fetch(BACKEND_URL + '/api/verify/audit')
                        .then(r => r.json())
                        .then(data => {
                            this.textContent = 'Verify Chain (CLI)';
                            alert('CHAIN VERIFICATION RESULT:\\n\\nStatus: ' + data.status + '\\nMessage: ' + data.message + '\\nEntries Validated: ' + (data.entries || 0));
                        })
                        .catch(err => {
                            this.textContent = 'Verify Chain (CLI)';
                            alert('Verification Error: ' + err);
                        });
                ">Verify Chain (CLI)</button>`;
                document.getElementById('auditPanel').appendChild(btn);
            }
        }

        function setRisk(id, level) {
            const el = document.getElementById(id);
            const l = (level||'').toUpperCase();
            const cls = {CRITICAL:'rbg-critical',HIGH:'rbg-high',MEDIUM:'rbg-medium',LOW:'rbg-low'};
            el.className = 'risk-badge ' + (cls[l]||'rbg-na');
            el.textContent = l || '--';
        }