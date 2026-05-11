// script.js 파일
document.addEventListener('DOMContentLoaded', () => { 
    
    // ============================
    // 0. 모드 토글 관련 요소 셋업
    // ============================
    const modeToggleInput = document.getElementById('mode-toggle-input');
    const modeInput = document.getElementById('mode-input');
    const logo = document.querySelector('.logo-text');
    const labelDict = document.getElementById('label-dict');
    const labelEncy = document.getElementById('label-ency');

    // ============================
    // 0-1. 언어 선택 관련 요소 셋업 (✅ 추가)
    // ============================
    const nativeSelect = document.getElementById('native-lang-select');
    const targetSelect = document.getElementById('target-lang-select');
    const swapLangBtn = document.getElementById('swap-lang-btn');

    const langState = {
        native: 'ko',
        target: 'en'
    };

    function loadInitialLangs() {
        if (!nativeSelect || !targetSelect) return;

        const saved = JSON.parse(localStorage.getItem('sensedict_langs') || '{}');
        const browserLang = (navigator.language || '').slice(0, 2); // 'ko', 'en', ...

        langState.native = saved.native || (['ko', 'en', 'zh', 'de'].includes(browserLang) ? browserLang : 'ko');
        langState.target = saved.target || (langState.native === 'en' ? 'ko' : 'en');

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

    // 모드에 따라 언어 UI 상태 업데이트 (✅ 추가)
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

    // 언어 셀렉터 이벤트 바인딩 (✅ 추가)
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
        });

        if (swapLangBtn) {
            swapLangBtn.addEventListener('click', () => {
                const tmp = nativeSelect.value;
                nativeSelect.value = targetSelect.value;
                targetSelect.value = tmp;

                langState.native = nativeSelect.value;
                langState.target = targetSelect.value;
                saveLangs();
            });
        }
    }

    // ============================
    // 0-2. 모드 토글 동작
    // ============================
    if (modeToggleInput && modeInput && logo && labelDict && labelEncy) {
        // 초기 상태: 영어 사전 모드
        modeInput.value = 'dict';
        logo.classList.add('logo-mode-dict');
        document.body.classList.add('mode-dict');
        labelDict.classList.add('active');
        labelEncy.classList.remove('active');
        updateLangUIForMode(); // ✅ 초기 언어 UI 상태 반영

        // 토글 스위치를 직접 움직였을 때
        modeToggleInput.addEventListener('change', () => {
            if (modeToggleInput.checked) {
                // 백과사전 모드
                modeInput.value = 'encyclopedia';
                logo.classList.remove('logo-mode-dict');
                logo.classList.add('logo-mode-ency');
                document.body.classList.remove('mode-dict');
                document.body.classList.add('mode-ency');
                labelDict.classList.remove('active');
                labelEncy.classList.add('active');
            } else {
                // 영어 사전 모드
                modeInput.value = 'dict';
                logo.classList.remove('logo-mode-ency');
                logo.classList.add('logo-mode-dict');
                document.body.classList.remove('mode-ency');
                document.body.classList.add('mode-dict');
                labelEncy.classList.remove('active');
                labelDict.classList.add('active');
            }
            updateLangUIForMode(); // ✅ 모드 바뀔 때마다 언어 UI 업데이트
        });

        // 라벨 클릭으로도 토글 가능하게
        labelDict.addEventListener('click', () => {
            modeToggleInput.checked = false;
            modeToggleInput.dispatchEvent(new Event('change'));
        });

        labelEncy.addEventListener('click', () => {
            modeToggleInput.checked = true;
            modeToggleInput.dispatchEvent(new Event('change'));
        });
    }

    // ==============================
    // 1. 기존 검색 폼 로직 (언어 파라미터 추가)
    // ==============================
    const searchForm = document.getElementById('search-form');
    const educationSelect = document.getElementById('education-select');
    const fieldInput = document.getElementById('field-input');
    const searchInput = document.getElementById('search-input');

    // ✅ 기본 한국어 브라우저 메시지 대신 영어로 표시
    if (searchInput) {
        // required 조건 안 채우고 제출하려 할 때
        searchInput.addEventListener('invalid', (event) => {
            event.preventDefault(); // 기본 "이 입력란을 작성하세요." 막기
            searchInput.setCustomValidity('Please enter a word, sentence, or paragraph.');
        });

        // 사용자가 입력을 다시 하기 시작하면 오류 메시지 초기화
        searchInput.addEventListener('input', () => {
            searchInput.setCustomValidity('');
        });
    }

    // ✅ 자동 리사이즈: index.html에서 search-input이 textarea일 때만
    if (searchInput && searchInput.tagName === 'TEXTAREA') {
        const MAX_HEIGHT = 180; // CSS의 max-height와 맞춤

        const autoResize = () => {
            searchInput.style.height = 'auto';
            const newHeight = Math.min(searchInput.scrollHeight, MAX_HEIGHT);
            searchInput.style.height = newHeight + 'px';
            searchInput.style.overflowY =
                searchInput.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
        };

        autoResize();                            // 초기 한 번
        searchInput.addEventListener('input', autoResize);

        // Enter = 폼 제출, Shift+Enter = 줄바꿈
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                searchForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    if (searchForm) {
        searchForm.addEventListener('submit', async (event) => {
            event.preventDefault(); 
            
            const educationValue = educationSelect.value;
            const fieldValue = fieldInput.value;
            const searchValue = searchInput.value;
            const modeValue = modeInput ? modeInput.value : 'dict'; // 혹시 모드 인풋이 없을 경우 대비

            // ✅ 언어 값 읽기 (백과사전 모드면 target은 비워도 됨)
            const nativeValue = nativeSelect ? nativeSelect.value : 'ko';
            const targetValue = (targetSelect && !targetSelect.disabled) ? targetSelect.value : '';

            console.log('--- Search Info ---');
            console.log('Selected level:', educationValue);
            console.log('Field:', fieldValue);
            console.log('Query:', searchValue);
            console.log('Mode:', modeValue);
            console.log('Native language:', nativeValue);
            console.log('Target language:', targetValue);

            const params = new URLSearchParams({
                education: educationValue,
                field: fieldValue,
                query: searchValue,
                mode: modeValue,
                native_lang: nativeValue,
                target_lang: targetValue
            });

            // window.location.href = `results.html?${params.toString()}`;
            window.location.href = `/result?${params.toString()}`;
        });
    }

    // ==============================
    // 2. I'm Feeling Lucky 버튼 로직
    // ==============================

    const fortunes = [
    "Today is the perfect balance of studying and relaxing! ⚖️",
    "Order fried chicken with zero guilt. You're the main character today! 🍗",
    "A short walk will bring unexpected luck. 🚶‍♀️🌿",
    "Everything seems to fall perfectly into place today. ✨",
    "You'll feel more focused than usual. Your mind is crystal clear! ☀️",
    "One good song might decide the mood of your entire day. 🎧",
    "A cup of coffee will recharge your energy by 200%. ☕⚡",
    "Today you have both the ‘study buff’ and the ‘luck buff’ ON! 🧠🍀",
    "You'll receive an unexpected compliment. 😊",
    "Your subway seat luck is at its peak! Today is a lucky day. 🚆🍀",
    "Luck will help you more than effort today. 🎯",
    "A clear sky will lift your spirits. ☁️💙",
    "Small mistakes will be forgiven easily today. 😅",
    "Every smile you make will attract something good. 😄",
    "A random phrase you hear might become a useful hint. 💬",
    "Whether it's a test or daily tasks, today is on your side. 🙌",
    "Finishing one postponed task will bring an unexpected reward. 🎁",
    "Today's TMI becomes tomorrow's fun story. 🗣️",
    "Good things will show up without warning. Are you ready? 🎈",
    "The day may feel a bit longer—in a good way. 🌇",
    "'It’ll be okay' actually comes true today. 🌈",
    "Something you start lightly will turn into a surprising achievement. 💪",
    "Of all days, your hair looks great today. ✂️😎",
    "This moment will become a ‘good memory’ later. 📸",
    "Your concentration is twice as strong today! 📚⚡",
    "Something pleasant arrives without notice. 🎁",
    "Order fried chicken with zero guilt. You're the main character today! 🍗",
    "Your mind feels refreshed. Even complicated tasks go smoothly. ☀️",
    "Even small mistakes will look cute today. 😆",
    "The smell of coffee feels unusually sweet. ☕💫",
    "Everything you study is saved straight to your brain. 🧠💾",
    "A friend's short comment will unexpectedly comfort you. 💬",
    "Today is the perfect blend of luck and skill! 🎯",
    "Everything progresses exactly as planned. ✅",
    "A thought during a walk might become a life tip. 🌿",
    "A short nap brings a genius-level idea. 😴💡",
    "Your smile shines brighter than your fortune today. 😄",
    "Good news may come if you wake up early! ⏰",
    "Everything feels fun today, no matter what you do. 🎨",
    "It’s okay to slow down today. Enjoy the pace. 🌈",
    "A good opportunity starts from a casual conversation. 🗣️",
    "You might receive an unexpected compliment today. 🌸",
    "A sentence in a book will read your heart perfectly. 📖💫",
    "Doing ‘just a little’ today turns out to be surprisingly efficient. ⏳",
    "Light exercise will change the whole day. 🏃‍♀️",
    "A clear sky helps you organize your thoughts. ☁️",
    "Today's mistakes become tomorrow's memes. 😂",
    "Perfect weather to study. (So… you should, right?) 🌞",
    "A random song will reset your mood. 🎶",
    "A new encounter will brighten your day. 💕",
    "Today, even a simple meal tastes amazing. Happiness starts with good food! 🍱",
    "A small achievement becomes a huge motivation. 🏆",
    "Follow your heart today—it won’t lead you wrong. 🌿",
    "Even playing around feels productive today. 😎",
    "A difficult problem feels strangely interesting today! 🤔✨",
    "Your sense of humor is at its peak. You’re the star today! 🪩",
    "Planning your studies might help you see your life plan, too. 📋",
    "Doing ‘just enough’ is more than enough today. No overdoing it! 🚫",
    "Rest is part of studying. Today is a day of reasonable laziness. 🛋️",
    "Your subway seat luck is amazing today. Everything goes smoothly. 🚆🍀",
    "Your words carry extra weight today. 💬✨",
    "A small act of kindness returns to you greatly. 🤝",
    "Your heart, not your head, will give you the answer today. ❤️",
    "Good news will find you this afternoon. Wait for it. ⏳📩",
    "Deadline worries fade—everything gets handled in order. 📂",
    "Luck follows the number of times you laugh today. 😊🍀",
    "A ‘why not?’ moment becomes a great photo. 📸",
    "It's the perfect day to build a good habit. 🧘",
    "You look pretty cool today—just saying. 😌",
    "Even the clouds look like they're on your side. ☁️💙",
    "Unexpected events take a good turn today. 🔄✨",
    "If you feel okay, you've already won half the day. 🌞",
    "You're in ‘lucky main character mode’ today! 🎬",
    "Every beginning starts on an ordinary day—like today. 🌱"
    ];

    const luckyButton = document.getElementById('lucky-button');

    if (luckyButton) {
        luckyButton.addEventListener('click', () => {
            const randomIndex = Math.floor(Math.random() * fortunes.length);
            const todayFortune = fortunes[randomIndex];

            alert(`✨ Today's Fortune ✨\n\n${todayFortune}`);
        });
    }
});
