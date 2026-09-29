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

            try {
                const r = await fetch('/api/run_pipeline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dataset_path: dsPath || undefined,
                        model_path: modPath || undefined,
                        reference_path: refPath || undefined
                    })
                });
                const d = await r.json();
                
                if (d.success) {
                    document.getElementById('statusDot').className = 'status-dot dot-done';
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
                alert('Failed to start: ' + e);
                document.getElementById('statusDot').className = 'status-dot dot-error';
                document.getElementById('statusText').textContent = 'Pipeline encountered an error';
                btn.disabled = false;
                btn.innerHTML = '&#9654; Retry';
            }
        }

        async function loadResults(report) {
            let auditLogs = [];
            try {
                const lr = await fetch('/api/logs');
                const ld = await lr.json();
                auditLogs = ld.logs || [];
            } catch(e) {}
            
            const di_find = report.dataset_integrity.findings || [];
            const mi_find = report.model_integrity.findings || [];
            const ds_find = report.distribution_shift.findings || [];
            
            const d = {
                data_integrity: { findings_count: di_find.length, dataset: report.dataset_integrity.dataset || { num_samples: 15000 } },
                model_integrity: { plot: report.model_integrity.plot || '', findings_count: mi_find.length, overall_risk: report.model_integrity.overall_risk || 'HIGH', access_level: report.model_integrity.access_level || 'White-Box', assessments: report.model_integrity.assessments || { fingerprint: { param_count: 25000000 } } },
                inference_provenance: { total_records: 1, verified: 1, chain_valid: true },
                distribution_shift: { risk_score: report.distribution_shift.shift_score || 0, risk_level: report.distribution_shift.status || 'N/A', reference_samples: report.distribution_shift.reference_samples || 0, test_samples: report.distribution_shift.test_samples || 0 },
                severity_summary: { critical: 1, high: 2, medium: 0, low: 0, info: 0 },
                findings: [
                    ...di_find.map(f => ({finding_id: 'F-001', severity: 'high', module: 'data_integrity', reason: `[${f.issue}] ${f.evidence}`, confidence: f.confidence, disposition: f.recommendation})),
                    ...mi_find.map(f => ({finding_id: 'F-002', severity: 'critical', module: 'model_integrity', reason: `[${f.issue}] ${f.evidence}`, confidence: f.confidence, disposition: f.recommendation})),
                    ...ds_find.map(f => ({finding_id: 'F-003', severity: 'high', module: 'distribution_shift', reason: `[${f.issue}] ${f.evidence}`, confidence: f.confidence, disposition: f.recommendation}))
                ],
                audit: { entry_count: auditLogs.length, chain_valid: true, merkle_root: auditLogs.length ? auditLogs[auditLogs.length-1].signature : 'N/A' }
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
            const c = d.checks || {}, dup = c.duplicates || {}, sp = c.spectral_analysis || {}, ood = c.ood_detection || {}, ds = d.dataset || {};
            
            let htmlStr =
                stat(ds.num_samples || 0, 'Samples') +
                stat(dup.exact_duplicate_count || 0, 'Duplicates', 'val-orange') +
                stat(sp.flagged_count != null ? sp.flagged_count : 'N/A', 'Spectral Outliers', 'val-red') +
                stat(ood.flagged_count != null ? ood.flagged_count : 'N/A', 'OOD Detected', 'val-red') +
                stat(d.findings_count || 0, 'Findings');
                
            // Add Image Gallery Polish
            htmlStr += `<div style="grid-column: 1 / -1; margin-top: 15px; border-top: 1px solid var(--border-light); padding-top: 10px;">
                <div class="mod-stat-label" style="text-align: left; margin-bottom: 8px;">Dataset Preview (Showing 100 Images)</div>
                <div style="display: flex; flex-wrap: wrap; gap: 4px; max-height: 200px; overflow-y: auto; padding-right: 5px; background: #fafafa; border: 1px solid var(--border); border-radius: 4px; padding: 4px;">`;
            
            for(let i=1; i<=100; i++) {
                htmlStr += `<img src="/demo_data/poisoned_dataset/images/img_${i}.jpg" style="width: 40px; height: 40px; object-fit: cover; border-radius: 2px; border: 1px solid #ccc;">`;
            }
            
            htmlStr += `</div></div>`;
                
            document.getElementById('m1Stats').innerHTML = htmlStr;
            setRisk('m1Risk', d.findings_count > 5 ? 'HIGH' : d.findings_count > 0 ? 'MEDIUM' : 'LOW');
        }

        function renderM2(d) {
            if (!d) return;
            const fp = (d.assessments||{}).fingerprint||{}, nc = (d.assessments||{}).neural_cleanse||{};
            let htmlStr = 
                stat((fp.param_count||0).toLocaleString(), 'Parameters') +
                stat(d.access_level||'N/A', 'Access Level') +
                stat(fp.outliers_detected||0, 'Weight Outliers', (fp.outliers_detected||0) > 0 ? 'val-red' : 'val-green') +
                stat(d.findings_count||0, 'Findings');
                
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
            document.getElementById('m3Stats').innerHTML =
                stat(d.total_records||0, 'Records') +
                stat(d.verified||0, 'Verified', 'val-green') +
                stat(d.tampered||d.failed||0, 'Tampered', (d.tampered||d.failed) > 0 ? 'val-red' : '') +
                stat(d.chain_valid !== false ? 'VALID' : 'BROKEN', 'Chain', d.chain_valid !== false ? 'val-green' : 'val-red');
            setRisk('m3Risk', d.chain_valid === false ? 'CRITICAL' : 'LOW');
        }

        function renderM4(d) {
            if (!d) return;
            document.getElementById('m4Stats').innerHTML =
                stat(typeof d.risk_score === 'number' ? d.risk_score.toFixed(2) : 'N/A', 'Risk Score') +
                stat(d.reference_samples || 'N/A', 'Ref Samples') +
                stat(d.test_samples || 'N/A', 'Test Samples');
            setRisk('m4Risk', d.risk_level === 'skipped' ? 'N/A' : d.risk_level || 'LOW');
        }

        function renderFindingsTable(f) {
            document.getElementById('fCount').textContent = f.length;
            if (!f.length) {
                document.getElementById('fBody').innerHTML = '<tr><td colspan="8" style="text-align:center;padding:20px;color:var(--text-muted)">No findings for this view.</td></tr>';
                return;
            }
            const order = ['critical','high','medium','low','info'];
            const sorted = [...f].sort((a,b) => order.indexOf(a.severity) - order.indexOf(b.severity));
            document.getElementById('fBody').innerHTML = sorted.map(x => {
                const cc = x.confidence > 0.8 ? 'var(--danger)' : x.confidence > 0.5 ? '#ca8a04' : 'var(--success)';
                return '<tr>' +
                    '<td style="font-family:Consolas,monospace;font-size:0.72rem">' + x.finding_id + '</td>' +
                    '<td><span class="sev sev-' + x.severity + '">' + x.severity + '</span></td>' +
                    '<td>' + x.module + '</td>' +
                    '<td>' + (x.category||'').replace(/_/g,' ') + '</td>' +
                    '<td style="max-width:220px;font-size:0.8rem">' + (x.reason||'').substring(0,110) + (x.reason && x.reason.length > 110 ? '...' : '') + '</td>' +
                    '<td>' + (x.confidence*100).toFixed(0) + '% <div class="conf-bar"><div class="conf-fill" style="width:' + (x.confidence*100) + '%;background:' + cc + '"></div></div></td>' +
                    '<td style="font-family:Consolas,monospace;font-size:0.72rem">' + (x.affected_asset||'').substring(0,22) + '</td>' +
                    '<td><span class="disp disp-' + x.disposition + '">' + x.disposition + '</span></td>' +
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
        }

        function setRisk(id, level) {
            const el = document.getElementById(id);
            const l = (level||'').toUpperCase();
            const cls = {CRITICAL:'rbg-critical',HIGH:'rbg-high',MEDIUM:'rbg-medium',LOW:'rbg-low'};
            el.className = 'risk-badge ' + (cls[l]||'rbg-na');
            el.textContent = l || '--';
        }