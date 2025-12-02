// results.js
document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const education = params.get('education') || 'bachelor';
    const field = params.get('field') || '';
    const query = params.get('query') || '';
    const mode = params.get('mode') || 'dict'; // dict / encyclopedia

    // ✅ 언어 파라미터
    const nativeLang = params.get('native_lang') || 'ko';
    const targetLang = params.get('target_lang') || '';

    const langNameMap = {
        ko: 'Korean',
        en: 'English',
        zh: 'Chinese',
        de: 'German'
    };

    // 유틸: XSS 방지용 간단 escape
    const esc = (s) => (typeof s === 'string')
        ? s.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))
        : s;

    // ============================
    // 0-1. 언어 선택 관련 요소
    // ============================
    const nativeSelect = document.getElementById('native-lang-select');
    const targetSelect = document.getElementById('target-lang-select');
    const swapLangBtn = document.getElementById('swap-lang-btn');

    // 나중에 참조해야 하므로 먼저 선언
    const modeInput = document.getElementById('mode-input');

    const langState = {
        native: nativeLang,
        target: targetLang || (nativeLang === 'en' ? 'ko' : 'en')
    };

    function loadInitialLangs() {
        if (!nativeSelect || !targetSelect) return;

        const saved = JSON.parse(localStorage.getItem('sensedict_langs') || '{}');

        if (saved.native) langState.native = saved.native;
        if (saved.target) langState.target = saved.target;

        if (langState.native === langState.target) {
            langState.target = (langState.native === 'ko') ? 'en' : 'ko';
        }

        nativeSelect.value = langState.native;
        targetSelect.value = langState.target;
    }

    function saveLangs() {
        if (!nativeSelect || !targetSelect) return;
        localStorage.setItem('sensedict_langs', JSON.stringify({
            native: langState.native,
            target: langState.target
        }));
    }

    function updateLangUIForMode() {
        if (!targetSelect || !swapLangBtn || !modeInput) return;
        if (modeInput.value === 'encyclopedia') {
            targetSelect.disabled = true;
            swapLangBtn.disabled = true;
        } else {
            targetSelect.disabled = false;
            swapLangBtn.disabled = false;
        }
    }

    // 언어 셀렉터 이벤트 바인딩
    if (nativeSelect && targetSelect) {
        loadInitialLangs();

        nativeSelect.addEventListener('change', () => {
            const newNative = nativeSelect.value;

            if (newNative === targetSelect.value) {
                const candidates = Array.from(targetSelect.options)
                    .map(o => o.value)
                    .filter(v => v !== newNative);
                if (candidates.length > 0) {
                    targetSelect.value = candidates[0];
                    langState.target = candidates[0];
                }
            }

            langState.native = newNative;
            saveLangs();
            updateLangSummary();
        });

        targetSelect.addEventListener('change', () => {
            const newTarget = targetSelect.value;

            if (newTarget === nativeSelect.value) {
                const candidates = Array.from(nativeSelect.options)
                    .map(o => o.value)
                    .filter(v => v !== newTarget);
                if (candidates.length > 0) {
                    nativeSelect.value = candidates[0];
                    langState.native = candidates[0];
                }
            }

            langState.target = newTarget;
            saveLangs();
            updateLangSummary();
        });

        if (swapLangBtn) {
            swapLangBtn.addEventListener('click', () => {
                const tmp = nativeSelect.value;
                nativeSelect.value = targetSelect.value;
                targetSelect.value = tmp;

                langState.native = nativeSelect.value;
                langState.target = targetSelect.value;
                saveLangs();
                updateLangSummary();
            });
        }
    }

    // ============================
    // 0. 모드 토글 / 로고 초기화
    // ============================
    const logo = document.querySelector('.logo-text');
    const modeToggleInput = document.getElementById('mode-toggle-input');
    const labelDict = document.getElementById('label-dict');
    const labelEncy = document.getElementById('label-ency');
    const root = document.body;

    const applyModeClass = (m) => {
        root.classList.remove('mode-dict', 'mode-ency');
        root.classList.add(m === 'encyclopedia' ? 'mode-ency' : 'mode-dict');
    };

    if (logo && modeToggleInput && modeInput && labelDict && labelEncy) {
        if (mode === 'encyclopedia') {
            modeToggleInput.checked = true;
            modeInput.value = 'encyclopedia';
            logo.classList.add('logo-mode-ency');
            labelEncy.classList.add('active');
            labelDict.classList.remove('active');
        } else {
            modeToggleInput.checked = false;
            modeInput.value = 'dict';
            logo.classList.add('logo-mode-dict');
            labelDict.classList.add('active');
            labelEncy.classList.remove('active');
        }
        applyModeClass(mode);
        updateLangUIForMode();

        modeToggleInput.addEventListener('change', () => {
            if (modeToggleInput.checked) {
                modeInput.value = 'encyclopedia';
                logo.classList.remove('logo-mode-dict');
                logo.classList.add('logo-mode-ency');
                labelDict.classList.remove('active');
                labelEncy.classList.add('active');
                applyModeClass('encyclopedia');
            } else {
                modeInput.value = 'dict';
                logo.classList.remove('logo-mode-ency');
                logo.classList.add('logo-mode-dict');
                labelEncy.classList.remove('active');
                labelDict.classList.add('active');
                applyModeClass('dict');
            }
            updateLangUIForMode();
        });

        labelDict.addEventListener('click', () => {
            modeToggleInput.checked = false;
            modeToggleInput.dispatchEvent(new Event('change'));
        });

        labelEncy.addEventListener('click', () => {
            modeToggleInput.checked = true;
            modeToggleInput.dispatchEvent(new Event('change'));
        });
    }

    // ============================
    // 1. 요약 / 폼 값 세팅
    // ============================
    const educationMap = {
        elementary: 'Elementary',
        middle: 'Middle school',
        high: 'High school',
        bachelor: 'Bachelor',
        master: 'Master',
        doctor: 'PhD'
    };
    const educationText = educationMap[education] || 'Not selected';

    document.getElementById('summary-education').textContent = educationText;
    document.getElementById('summary-field').textContent = field || 'Not specified';
    document.getElementById('summary-query').textContent = query || '(No query entered)';

    // ✅ 언어 요약
    const langSummaryEl = document.getElementById('summary-lang');

    function updateLangSummary() {
        if (!langSummaryEl) return;

        const currentNative = nativeSelect ? nativeSelect.value : nativeLang;
        const currentTarget =
            (targetSelect && !targetSelect.disabled)
                ? targetSelect.value
                : (targetLang || '');

        const nativeLabel = langNameMap[currentNative] || currentNative.toUpperCase();
        const targetLabel = currentTarget
            ? (langNameMap[currentTarget] || currentTarget.toUpperCase())
            : '-';

        langSummaryEl.textContent = `${nativeLabel} → ${targetLabel}`;
    }

    updateLangSummary();

    const educationSelect = document.getElementById('education-select');
    const fieldInput = document.getElementById('field-input');
    const searchInput = document.getElementById('search-input');

    if (educationSelect) educationSelect.value = education;
    if (fieldInput) fieldInput.value = field;
    if (searchInput) searchInput.value = query;

    const searchForm = document.getElementById('results-search-form');
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const newEdu = educationSelect.value;
        const newField = fieldInput.value;
        const newQuery = searchInput.value;
        const currentMode = modeInput ? modeInput.value : mode;

        const currentNative = nativeSelect ? nativeSelect.value : nativeLang;
        const currentTarget =
            (targetSelect && !targetSelect.disabled)
                ? targetSelect.value
                : '';  // 백과사전 모드면 빈 문자열

        const newParams = new URLSearchParams({
            education: newEdu,
            field: newField,
            query: newQuery,
            mode: currentMode,
            native_lang: currentNative,
            target_lang: currentTarget
        });

        window.location.href = `/result?${newParams.toString()}`;
    });

    const resultDiv = document.getElementById('result-content');

    if (!query) {
        resultDiv.textContent = 'No query provided.';
        return;
    }

    // ============================
    // 2. 렌더링 유틸 함수들
    // ============================
    const renderExamplePairs = (pairs) => {
        if (!Array.isArray(pairs) || pairs.length === 0) return '';
        const items = pairs.map(ex => `
            <li class="example-item">
                <span class="example-sentence">${esc(ex.source_sentence || '')}</span><br>
                <span class="example-translation">${esc(ex.target_sentence || '')}</span>
            </li>
        `).join('');
        return `
            <p class="examples-title">Examples</p>
            <ul class="examples-list">${items}</ul>
        `;
    };

    const renderAlternativesList = (alts, title = 'Alternative expressions') => {
        if (!Array.isArray(alts) || alts.length === 0) return '';
        const items = alts.map(a => `<li>${esc(a)}</li>`).join('');
        return `
            <p class="examples-title">${title}</p>
            <ul class="alternative-list">${items}</ul>
        `;
    };

    const langBadgeShort = (code) => {
        if (!code) return '';
        const short = code.toUpperCase();
        return `<span class="lang-badge">${esc(short)}</span>`;
    };

    // ❗ Query 자체에 문제가 있을 때 보여줄 카드
    const renderQueryIssueCard = (qa) => {
        if (!qa) return '';

        const status = qa.status || 'UNKNOWN';
        const reason = qa.reason_l1 || '';
        const suggestions = Array.isArray(qa.suggestion_queries)
            ? qa.suggestion_queries
            : [];

        const statusLabelMap = {
            VALID: 'Valid query',
            TYPO: 'Possible typo',
            FACTUAL_ERROR: 'Factual error in the sentence',
            AMBIGUOUS: 'Ambiguous / underspecified query',
            NONSENSE: 'Nonsensical query',
        };
        const statusLabel = statusLabelMap[status] || status;

        const sugHtml = suggestions.length
            ? `
                <div class="query-issue-suggestions">
                    <p class="examples-title">Try searching for:</p>
                    <ul class="alternative-list">
                        ${suggestions.map(s => `<li>${esc(s)}</li>`).join('')}
                    </ul>
                </div>
              `
            : '';

        return `
            <article class="word-card query-issue-card">
                <p class="sentence-meta">
                    Status: <strong>${esc(statusLabel)}</strong>
                </p>
                ${reason
                    ? `<p class="sentence-explanation">${esc(reason)}</p>`
                    : ''
                }
                ${sugHtml}
            </article>
        `;
    };

    // ----------- 타입 가드들 -------------
    const isSentenceL1toL2 = (d) => {
        return d
            && d.sentence
            && typeof d.sentence.l1_sentence === 'string'
            && typeof d.sentence.main_l2_sentence === 'string'
            && Array.isArray(d.word_explanations);
    };

    const isSentenceL2toL1 = (d) => {
        return d
            && d.sentence
            && typeof d.sentence.l2_sentence === 'string'
            && typeof d.sentence.main_l1_sentence === 'string'
            && Array.isArray(d.word_explanations);
    };

    const isParagraphL1toL2 = (d) => {
        return d
            && typeof d.l1_paragraph === 'string'
            && Array.isArray(d.sentence_cards);
    };

    const isParagraphL2toL1 = (d) => {
        return d
            && typeof d.l2_paragraph === 'string'
            && typeof d.paragraph_l1_translation === 'string'
            && Array.isArray(d.sentence_cards);
    };

    const isWordDict = (d) => {
        return d
            && Array.isArray(d.entries)
            && d.entries.length > 0
            && typeof d.entries[0].source_text === 'string';
    };

    // ----------- 문장 렌더링 (L1→L2) -------------
    const renderSentenceL1toL2 = (data) => {
        const s = data.sentence || {};
        const l1 = s.l1_sentence || '';
        const l1Lang = s.l1_lang || nativeLang;
        const l2Lang = s.l2_lang || targetLang || '';
        const mainL2 = s.main_l2_sentence || '';
        const altL2 = s.alternative_l2_sentences || [];
        const words = data.word_explanations || [];

        const topHtml = `
            <article class="word-card sentence-card">
                <div class="sentence-block">
                    <div class="sentence-group">
                        <p class="sentence-meta">
                            ${langBadgeShort(l1Lang)} ${esc(langNameMap[l1Lang] || '')}
                            &rarr;
                            ${langBadgeShort(l2Lang)} ${esc(langNameMap[l2Lang] || '')}
                        </p>
                        <p class="sentence-original">
                            <strong>Original Sentence</strong><br>
                            ${esc(l1)}
                        </p>
                        <p class="sentence-text">
                            <strong>Generated Sentence</strong><br>
                            ${esc(mainL2)}
                        </p>
                        ${altL2.length > 0 ? `
                            <div class="sentence-alternatives-wrap">
                                <p class="examples-title">Alternative expressions</p>
                                <ul class="sentence-alternatives">
                                    ${altL2.map(a => `<li class="alt-line">${esc(a)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </article>
        `;

        const wordCards = words.map((w) => {
            const exHtml = renderExamplePairs(w.examples || []);
            const altsHtml = renderAlternativesList(w.alternatives_l2 || [], 'Alternative expressions');
            return `
                <article class="word-card word-explain-card">
                    <h3 class="word-title">${esc(w.l2_word || '')}</h3>
                    <div class="meaning-block">
                        <p class="meaning-text">${esc(w.meaning_l1 || '')}</p>
                        ${w.explanation_l1 ? `<p class="nuance-text">${esc(w.explanation_l1)}</p>` : ''}
                        ${altsHtml}
                        ${exHtml}
                    </div>
                </article>
            `;
        }).join('');

        return `
            <section class="card">
                ${topHtml}
                ${wordCards
                    ? `<h2 class="section-subtitle">Key Vocabulary</h2>
                       <div class="word-grid">${wordCards}</div>`
                    : `<p class="empty-hint">No word explanations.</p>`
                }
            </section>
        `;
    };

    // ----------- 문장 렌더링 (L2→L1) -------------
    const renderSentenceL2toL1 = (data) => {
        const s = data.sentence || {};
        const l2 = s.l2_sentence || '';
        const l2Lang = s.l2_lang || targetLang || '';
        const l1Lang = s.l1_lang || nativeLang;
        const mainL1 = s.main_l1_sentence || '';
        const expl = s.sentence_explanation_l1 || '';
        const words = data.word_explanations || [];

        const topHtml = `
            <article class="word-card sentence-card">
                <div class="sentence-block">
                    <div class="sentence-group">
                        <p class="sentence-meta">
                            ${langBadgeShort(l2Lang)} ${esc(langNameMap[l2Lang] || '')}
                            &rarr;
                            ${langBadgeShort(l1Lang)} ${esc(langNameMap[l1Lang] || '')}
                        </p>
                        <p class="sentence-original">
                            <strong>Original Sentence</strong><br>
                            ${esc(l2)}
                        </p>
                        <p class="sentence-text">
                            <strong>Translation</strong><br>
                            ${esc(mainL1)}
                        </p>
                        ${expl ? `
                            <p class="sentence-explanation">
                                <strong>Explanation</strong><br>
                                ${esc(expl)}
                            </p>
                        ` : ''}
                    </div>
                </div>
            </article>
        `;

        const wordCards = words.map((w) => {
            const exHtml = renderExamplePairs(w.examples || []);
            const altsHtml = renderAlternativesList(w.alternatives_l2 || [], 'Alternative expressions');
            return `
                <article class="word-card word-explain-card">
                    <h3 class="word-title">${esc(w.l2_word || '')}</h3>
                    <div class="meaning-block">
                        <p class="meaning-text">${esc(w.meaning_l1 || '')}</p>
                        ${w.explanation_l1 ? `<p class="nuance-text">${esc(w.explanation_l1)}</p>` : ''}
                        ${altsHtml}
                        ${exHtml}
                    </div>
                </article>
            `;
        }).join('');

        return `
            <section class="card">
                ${topHtml}
                ${wordCards
                    ? `<h2 class="section-subtitle">Key Vocabulary</h2>
                       <div class="word-grid">${wordCards}</div>`
                    : `<p class="empty-hint">No word explanations.</p>`
                }
            </section>
        `;
    };

    // ----------- 문단 렌더링 (보조: 문장 카드만) -------------
    const renderSentenceL1toL2Inner = (sentenceResp) => {
        const s = sentenceResp.sentence || {};
        const mainL2 = s.main_l2_sentence || '';
        const l1 = s.l1_sentence || '';
        const words = sentenceResp.word_explanations || [];

        const wordCards = words.map((w) => {
            const exHtml = renderExamplePairs(w.examples || []);
            const altsHtml = renderAlternativesList(w.alternatives_l2 || [], 'Alternative expressions');
            return `
                <article class="word-card word-explain-card">
                    <h4 class="word-title">${esc(w.l2_word || '')}</h4>
                    <div class="meaning-block">
                        <p class="meaning-text">${esc(w.meaning_l1 || '')}</p>
                        ${w.explanation_l1 ? `<p class="nuance-text">${esc(w.explanation_l1)}</p>` : ''}
                        ${altsHtml}
                        ${exHtml}
                    </div>
                </article>
            `;
        }).join('');

        return `
            <article class="word-card sentence-card">
                <div class="sentence-block">
                    <div class="sentence-group">
                        <p class="sentence-original">
                            <strong>Original Sentence</strong><br>${esc(l1)}
                        </p>
                        <p class="sentence-text">
                            <strong>Generated Sentence</strong><br>${esc(mainL2)}
                        </p>
                    </div>
                </div>
                ${wordCards ? `<div class="word-grid">${wordCards}</div>` : ''}
            </article>
        `;
    };

    const renderSentenceL2toL1Inner = (sentenceResp) => {
        const s = sentenceResp.sentence || {};
        const l2 = s.l2_sentence || '';
        const mainL1 = s.main_l1_sentence || '';
        const expl = s.sentence_explanation_l1 || '';
        const words = sentenceResp.word_explanations || [];

        const wordCards = words.map((w) => {
            const exHtml = renderExamplePairs(w.examples || []);
            const altsHtml = renderAlternativesList(w.alternatives_l2 || [], 'Alternative expressions');
            return `
                <article class="word-card word-explain-card">
                    <h4 class="word-title">${esc(w.l2_word || '')}</h4>
                    <div class="meaning-block">
                        <p class="meaning-text">${esc(w.meaning_l1 || '')}</p>
                        ${w.explanation_l1 ? `<p class="nuance-text">${esc(w.explanation_l1)}</p>` : ''}
                        ${altsHtml}
                        ${exHtml}
                    </div>
                </article>
            `;
        }).join('');

        return `
            <article class="word-card sentence-card">
                <div class="sentence-block">
                    <div class="sentence-group">
                        <p class="sentence-original">
                            <strong>Original Sentence</strong><br>${esc(l2)}
                        </p>
                        <p class="sentence-text">
                            <strong>Translation</strong><br>${esc(mainL1)}
                        </p>
                        ${expl ? `<p class="sentence-explanation">${esc(expl)}</p>` : ''}
                    </div>
                </div>
                ${wordCards ? `<div class="word-grid">${wordCards}</div>` : ''}
            </article>
        `;
    };

    // ----------- 문단 렌더링 (L1→L2) -------------
    const renderParagraphL1toL2 = (data) => {
        const cards = data.sentence_cards || [];
        const sentenceHtml = cards.map((c) => renderSentenceL1toL2Inner(c)).join('');

        return `
            <section class="card paragraph-card" data-paragraph-type="l1-l2">
                <h2 class="section-subtitle">Sentence-by-Sentence Generation & Vocabulary</h2>
                <div class="paragraph-sentence-indicator"></div>
                <div class="paragraph-sentence-container">
                    <div class="paragraph-sentence-track">
                        ${sentenceHtml || '<p class="empty-hint">No sentence cards available.</p>'}
                    </div>
                </div>
            </section>
        `;
    };

    // ----------- 문단 렌더링 (L2→L1) -------------
    const renderParagraphL2toL1 = (data) => {
        const l2Para = data.l2_paragraph || '';
        const l2Lang = data.l2_lang || targetLang || '';
        const l1Lang = data.l1_lang || nativeLang;
        const fullL1 = data.paragraph_l1_translation || '';
        const expl = data.paragraph_content_explanation_l1 || '';
        const cards = data.sentence_cards || [];

        const sentenceHtml = cards.map((c) => renderSentenceL2toL1Inner(c)).join('');

        return `
            <section class="card paragraph-card" data-paragraph-type="l2-l1">
                <article class="word-card">
                    <p class="sentence-meta">
                        ${langBadgeShort(l2Lang)} ${esc(langNameMap[l2Lang] || '')}
                        &rarr;
                        ${langBadgeShort(l1Lang)} ${esc(langNameMap[l1Lang] || '')}
                    </p>
                    <p><strong>Original Paragraph</strong><br>${esc(l2Para).replace(/\n/g, '<br>')}</p>
                    <p class="sentence-text">
                        <strong>Full Translation</strong><br>${esc(fullL1).replace(/\n/g, '<br>')}
                    </p>
                    ${expl ? `
                        <p class="sentence-explanation">
                            <strong>Paragraph Explanation</strong><br>
                            ${esc(expl).replace(/\n/g, '<br>')}
                        </p>
                    ` : ''}
                </article>

                <h2 class="section-subtitle">Sentence-by-Sentence Explanation & Vocabulary</h2>

                <div class="paragraph-sentence-indicator"></div>

                <div class="paragraph-sentence-container">
                    <div class="paragraph-sentence-track">
                        ${sentenceHtml || '<p class="empty-hint">No sentence cards available.</p>'}
                    </div>
                </div>
            </section>
        `;
    };

    // ----------- Word Dict 렌더링 -------------
    const renderWordDict = (data) => {
        const entries = data.entries || [];
        if (!entries.length) return '<p>No results available.</p>';

        const cardsHtml = entries.map((entry, idx) => {
            const variants = entry.variants || [];
            const title = entry.source_text || `(Entry ${idx + 1})`;
            const srcLang = entry.source_lang || nativeLang;
            const tgtLang = entry.target_lang || targetLang || '';

            const variantBlocks = variants.map((v) => {
                const exHtml = renderExamplePairs(v.examples || []);
                const altsHtml = renderAlternativesList(v.alternatives || [], 'Alternative expressions');
                return `
                    <div class="meaning-block">
                        ${v.target_text ? `<p class="meaning-text">${esc(v.target_text)}</p>` : ''}
                        ${v.explanation ? `<p class="nuance-text">${esc(v.explanation)}</p>` : ''}
                        ${altsHtml}
                        ${exHtml}
                    </div>
                `;
            }).join('');

            return `
                <article class="word-card">
                    <h3 class="word-title">${esc(title)}</h3>
                    <p class="sentence-meta">
                        ${langBadgeShort(srcLang)} ${esc(langNameMap[srcLang] || '')}
                        &rarr;
                        ${langBadgeShort(tgtLang)} ${esc(langNameMap[tgtLang] || '')}
                    </p>
                    ${variantBlocks}
                </article>
            `;
        }).join('');

        return cardsHtml;
    };

    const setupParagraphCarousels = () => {
        const sections = document.querySelectorAll('.paragraph-card');

        sections.forEach((section) => {
            const track = section.querySelector('.paragraph-sentence-track');
            if (!track) return;

            const cards = Array.from(track.querySelectorAll('.sentence-card'));
            if (cards.length === 0) return;

            const indicator = section.querySelector('.paragraph-sentence-indicator');
            let current = 0;

            if (indicator) {
                if (cards.length <= 1) {
                    indicator.style.display = 'none';
                } else {
                    indicator.innerHTML = cards.map((_, idx) =>
                        `<span class="page-dot${idx === 0 ? ' active' : ''}" data-index="${idx}"></span>`
                    ).join('');
                }
            }

            const updateView = () => {
                cards.forEach((card, idx) => {
                    card.style.display = (idx === current) ? 'block' : 'none';
                });

                if (indicator) {
                    const dots = indicator.querySelectorAll('.page-dot');
                    dots.forEach((dot, idx) => {
                        dot.classList.toggle('active', idx === current);
                    });
                }
            };

            updateView();

            track.addEventListener('click', (e) => {
                const rect = track.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const mid = rect.width / 2;

                if (x < mid) {
                    current = (current - 1 + cards.length) % cards.length;
                } else {
                    current = (current + 1) % cards.length;
                }
                updateView();
            });

            if (indicator) {
                indicator.addEventListener('click', (e) => {
                    const dot = e.target.closest('.page-dot');
                    if (!dot) return;
                    const idx = Number(dot.dataset.index);
                    if (!Number.isNaN(idx) && idx >= 0 && idx < cards.length) {
                        current = idx;
                        updateView();
                    }
                });
            }
        });
    };

    // ============================
    // 3. 데이터 요청 & 분기 렌더링
    // ============================
    try {
        const payload = {
            education: education,
            field,
            query,
            mode,
            native_lang: nativeLang,
            target_lang: targetLang
        };

        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.textContent = `An error occurred: ${data.error}`;
            return;
        }

        // 🔹 3-1) query_analysis 처리
        const qa = data.query_analysis || (data.sentence && data.sentence.query_analysis) || null;
        const status = qa?.status || "VALID";
        const reason_l1 = qa?.reason_l1 || "";
        const suggestions = qa?.suggestion_queries || null;

        const nonValidStatuses = ["TYPO", "FACTUAL_ERROR", "AMBIGUOUS", "NONSENSE"];

        if (nonValidStatuses.includes(status)) {
            const statusLabelMap = {
                TYPO: "Possible typo / misspelling",
                FACTUAL_ERROR: "Factual error in the sentence",
                AMBIGUOUS: "Ambiguous or underspecified query",
                NONSENSE: "Nonsensical or uninterpretable query",
            };
            const statusLabel = statusLabelMap[status] || status;

            const suggestionsHtml =
                Array.isArray(suggestions) && suggestions.length > 0
                    ? `
                        <div class="query-issue-suggestions">
                            <p class="examples-title">Try these instead:</p>
                            <ul class="alternative-list">
                                ${suggestions.map((s) => `<li>${esc(s)}</li>`).join("")}
                            </ul>
                        </div>
                    `
                    : "";

            resultDiv.innerHTML = `
                <section class="card query-issue-card">
                    <p class="sentence-meta">
                        <strong>Status:</strong> ${esc(statusLabel)}
                    </p>
                    <p class="sentence-explanation">
                        ${esc(reason_l1 || "")}
                    </p>
                    ${suggestionsHtml}
                </section>
            `;
            return;  // INVALID이면 여기서 종료
        }


        // 🔹 A) 백과사전 모드
        if (mode === 'encyclopedia') {
            const {
                input_text = '',
                key_terms = [],
                simplified_explanation = '',
                usage_context = '',
                extra_notes = '',
            } = data;

            let html = '';

            if (input_text) {
                html += `<p><strong>Original Text</strong><br>${esc(input_text)}</p>`;
            }

            if (Array.isArray(key_terms) && key_terms.length > 0) {
                html += `<hr><p><strong>Key Concepts</strong></p><ul>`;
                key_terms.forEach((termObj) => {
                    html += `<li><strong>${esc(termObj.term || '')}</strong>: ${esc(termObj.definition || '')}`;
                    if (termObj.analogy) {
                        html += `<br><em>Analogy:</em> ${esc(termObj.analogy)}`;
                    }
                    html += `</li>`;
                });
                html += `</ul>`;
            }

            if (simplified_explanation) {
                html += `<hr><p><strong>Simplified Explanation</strong><br>${esc(simplified_explanation).replace(/\n/g, '<br>')}</p>`;
            }

            if (usage_context) {
                html += `<p><strong>Common Usage / Where It Is Used</strong><br>${esc(usage_context).replace(/\n/g, '<br>')}</p>`;
            }

            if (extra_notes) {
                html += `<p><strong>Additional Notes</strong><br>${esc(extra_notes).replace(/\n/g, '<br>')}</p>`;
            }

            resultDiv.innerHTML = '';
            const card = document.createElement('article');
            card.className = 'word-card';
            card.tabIndex = 0;
            card.innerHTML = html || 'No explanation available.';
            resultDiv.appendChild(card);
            return;
        }

        // 🔹 B) 문장 / 문단 / 단어 모드 분기
        if (isSentenceL1toL2(data)) {
            resultDiv.innerHTML = renderSentenceL1toL2(data);
            return;
        }

        if (isSentenceL2toL1(data)) {
            resultDiv.innerHTML = renderSentenceL2toL1(data);
            return;
        }

        if (isParagraphL1toL2(data)) {
            resultDiv.innerHTML = renderParagraphL1toL2(data);
            setupParagraphCarousels();
            return;
        }

        if (isParagraphL2toL1(data)) {
            resultDiv.innerHTML = renderParagraphL2toL1(data);
            setupParagraphCarousels();
            return;
        }

        if (isWordDict(data)) {
            resultDiv.innerHTML = renderWordDict(data);
            return;
        }

        // 🔹 Fallback: 텍스트 응답
        const text = data.result || JSON.stringify(data, null, 2);
        const html = text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');
        resultDiv.innerHTML = html;

    } catch (err) {
        console.error(err);
        resultDiv.textContent = 'An error occurred during the request. Please try again later.';
    }

    // ============================
    // 4. 카드 선택 토글 (공통)
    // ============================
    resultDiv.addEventListener('click', (e) => {
        const cardEl = e.target.closest('.word-card');
        if (!cardEl) return;

        resultDiv.querySelectorAll('.word-card.is-selected').forEach(el => {
            el.classList.remove('is-selected');
        });
        cardEl.classList.add('is-selected');
    });
});
