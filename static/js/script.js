// =================== STATE ===================
let selectedArtist = null;
let selectedDifficulty = 'easy';
let questions = [];
let currentIndex = 0;
let results = []; // {correct: bool, trackName: string, userAnswer: string}
let gameActive = false;
let currentArtistNote = null;

// Zorluk bazlı dinleme süresi (saniye)
function getPlayDuration() {
    return { easy: 7, medium: 5, hard: 3 }[selectedDifficulty] ?? 5;
}

// Otomatik domain algılama (localhost ise port 8000, deploy edildiyse o anki domain)
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000/api'
    : window.location.origin + '/api';

// =================== LUCKY / POPULAR ARTISTS ===================
const POPULAR_ARTISTS = [
    { id: '13', name: 'Eminem', images: [{ url: 'https://e-cdns-images.dzcdn.net/images/artist/19cc5e5e1f7c8b9d4b3cec64c68c7eb1/250x250-000000-80-0-0.jpg' }] },
    { id: '384236', name: 'The Weeknd', images: [{ url: 'https://e-cdns-images.dzcdn.net/images/artist/1ef3c7f17f67b2f0a4f8f5c1b0e1b5e4/250x250-000000-80-0-0.jpg' }] },
    { id: '27', name: 'Daft Punk', images: [{ url: '' }] },
    { id: '564', name: 'Rihanna', images: [{ url: '' }] },
    { id: '75798', name: 'Drake', images: [{ url: '' }] },
    { id: '246791', name: 'Billie Eilish', images: [{ url: '' }] },
    { id: '1118546', name: 'Ed Sheeran', images: [{ url: '' }] },
    { id: '860', name: 'Coldplay', images: [{ url: '' }] },
    { id: '7499', name: 'Taylor Swift', images: [{ url: '' }] },
    { id: '14208', name: 'Ariana Grande', images: [{ url: '' }] },
    { id: '167', name: 'Madonna', images: [{ url: '' }] },
    { id: '259', name: 'Radiohead', images: [{ url: '' }] },
    { id: '410431', name: 'Post Malone', images: [{ url: '' }] },
    { id: '1032731', name: 'Bad Bunny', images: [{ url: '' }] },
    { id: '144', name: 'David Bowie', images: [{ url: '' }] },
    { id: '5521', name: 'Linkin Park', images: [{ url: '' }] },
    { id: '4614', name: 'Adele', images: [{ url: '' }] },
    { id: '1424', name: 'Michael Jackson', images: [{ url: '' }] },
    { id: '411', name: 'Metallica', images: [{ url: '' }] },
    { id: '357', name: 'Red Hot Chili Peppers', images: [{ url: '' }] },
];

// =================== ELEMENTS ===================
const searchInput = document.getElementById('artist-search');
const resultsDropdown = document.getElementById('search-results');
const diffBtns = document.querySelectorAll('.diff-btn');
const startBtn = document.getElementById('start-game');
const setupScreen = document.getElementById('setup-screen');
const gameScreen = document.getElementById('game-screen');
const resultScreen = document.getElementById('result-screen');
const audioPlayer = document.getElementById('audio-player');
const progressBar = document.getElementById('playback-progress');
const optionsContainer = document.getElementById('options-container');
const nextBtn = document.getElementById('next-btn');
const playAgainBtn = document.getElementById('play-again');
const currentQEl = document.getElementById('current-q');
const totalQEl = document.getElementById('total-q');
const statusText = document.getElementById('game-status-text');
const questionTracker = document.getElementById('question-tracker');

// =================== SEARCH ===================
let searchTimeout;
searchInput.addEventListener('input', e => {
    clearTimeout(searchTimeout);
    const q = e.target.value.trim();
    if (q.length < 2) { resultsDropdown.classList.add('hidden'); return; }
    searchTimeout = setTimeout(() => searchArtist(q), 400);
});

// Dropdown kapatma
document.addEventListener('click', e => {
    if (!e.target.closest('.search-box')) resultsDropdown.classList.add('hidden');
});

async function searchArtist(query) {
    try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        renderSearchResults(data.artists.items);
    } catch (err) { console.error('Search error:', err); }
}

function renderSearchResults(artists) {
    resultsDropdown.innerHTML = '';
    if (!artists || artists.length === 0) { resultsDropdown.classList.add('hidden'); return; }
    artists.forEach(artist => {
        const div = document.createElement('div');
        div.className = 'result-item';
        const img = artist.images[0]?.url || '';
        div.innerHTML = `
            <img src="${img}" alt="${artist.name}" onerror="this.style.display='none'">
            <span>${artist.name}</span>`;
        div.onclick = () => selectArtist(artist);
        resultsDropdown.appendChild(div);
    });
    resultsDropdown.classList.remove('hidden');
}

function selectArtist(artist) {
    selectedArtist = artist;
    searchInput.value = artist.name;
    resultsDropdown.classList.add('hidden');
    startBtn.disabled = false;
}

// =================== DIFFICULTY ===================
diffBtns.forEach(btn => {
    btn.onclick = () => {
        diffBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedDifficulty = btn.dataset.level;
    };
});

// =================== START GAME ===================
startBtn.onclick = startGame;

async function startGame() {
    if (!selectedArtist) return;
    startBtn.textContent = 'Yükleniyor...';
    startBtn.disabled = true;

    // Loading Trivia Ekle
    let triviaEl = document.getElementById('loading-trivia');
    if (!triviaEl) {
        triviaEl = document.createElement('div');
        triviaEl.id = 'loading-trivia';
        startBtn.insertAdjacentElement('afterend', triviaEl);
    }
    triviaEl.style.display = 'block';

    const loadingMessages = [
        "Plaklar tozdan arındırılıyor...",
        "Sanatçı kulisten çağrılıyor...",
        "Nota sehpaları düzeltiliyor...",
        "Deezer arşivi taranıyor...",
        "Mikrofon kabloları çözülüyor..."
    ];
    let msgIndex = 0;
    triviaEl.textContent = loadingMessages[msgIndex];
    triviaEl.className = 'fade-anim';

    const triviaInterval = setInterval(() => {
        msgIndex = (msgIndex + 1) % loadingMessages.length;
        triviaEl.classList.remove('fade-anim');
        void triviaEl.offsetWidth; // Trigger reflow
        triviaEl.textContent = loadingMessages[msgIndex];
        triviaEl.classList.add('fade-anim');
    }, 750);

    // Zorunlu 3 saniye bekleme
    await new Promise(res => setTimeout(res, 3000));

    try {
        const res = await fetch(`${API_BASE}/quiz?artist_id=${selectedArtist.id}&difficulty=${selectedDifficulty}&count=10`);
        if (!res.ok) {
            const err = await res.json();
            alert(err.detail || 'Oyun başlatılamadı.');
            startBtn.textContent = 'Oyunu Başlat';
            startBtn.disabled = false;
            clearInterval(triviaInterval);
            triviaEl.style.display = 'none';
            return;
        }
        const data = await res.json();
        questions = data.questions;
        currentIndex = 0;
        results = [];

        totalQEl.textContent = questions.length;
        buildTracker(questions.length);

        setupScreen.classList.add('hidden');
        gameScreen.classList.remove('hidden');
        resultScreen.classList.add('hidden');

        loadQuestion(currentIndex);
    } catch (err) {
        console.error('Start error:', err);
        alert('Bağlantı hatası!');
        startBtn.textContent = 'Oyunu Başlat';
        startBtn.disabled = false;
    } finally {
        clearInterval(triviaInterval);
        triviaEl.style.display = 'none';
    }
}

// =================== TRACKER ===================
function buildTracker(count) {
    questionTracker.innerHTML = '';
    for (let i = 0; i < count; i++) {
        const dot = document.createElement('div');
        dot.className = 'tracker-dot';
        dot.textContent = i + 1;
        dot.id = `dot-${i}`;
        questionTracker.appendChild(dot);
    }
}

function updateTracker(index, isCorrect) {
    const dot = document.getElementById(`dot-${index}`);
    if (dot) {
        dot.classList.remove('active');
        dot.classList.add(isCorrect ? 'dot-correct' : 'dot-wrong');
    }
}

function setActiveDot(index) {
    document.querySelectorAll('.tracker-dot').forEach(d => d.classList.remove('active'));
    const dot = document.getElementById(`dot-${index}`);
    if (dot) dot.classList.add('active');
}

// =================== LOAD QUESTION ===================
function loadQuestion(index) {
    const q = questions[index];
    gameActive = true;

    currentQEl.textContent = index + 1;
    statusText.textContent = 'Dinle ve bil!';
    nextBtn.classList.add('hidden');
    optionsContainer.innerHTML = '';
    progressBar.style.width = '0%';
    setActiveDot(index);

    // Seçenekler
    q.options.forEach(option => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.textContent = option;
        btn.onclick = () => handleGuess(btn, option, q.correct_answer);
        optionsContainer.appendChild(btn);
    });

    // Ses
    audioPlayer.src = q.audio_url;
    audioPlayer.currentTime = 0;
    // Süre etiketini zorluk bazlı güncelle
    const dur = getPlayDuration();
    document.querySelector('.time-info').textContent = `0:00 / 0:0${dur}`;
    audioPlayer.play().catch(e => console.warn('Autoplay blocked:', e));
    startProgress();
}

// =================== AUDIO PROGRESS ===================
let progressInterval = null;

function startProgress() {
    clearInterval(progressInterval);
    const dur = getPlayDuration();
    progressInterval = setInterval(() => {
        if (!gameActive) { clearInterval(progressInterval); return; }
        const pct = (audioPlayer.currentTime / dur) * 100;
        progressBar.style.width = `${Math.min(pct, 100)}%`;
        if (audioPlayer.currentTime >= dur) {
            audioPlayer.pause();
            clearInterval(progressInterval);
            if (gameActive) {
                statusText.innerHTML = `Süre doldu! <button id="replay-btn" class="replay-icon-btn" title="Tekrar Dinle" style="display: inline-flex; align-items: center; justify-content: center; background: rgba(29, 185, 84, 0.2); border: none; border-radius: 50%; padding: 4px; margin-left: 6px; cursor: pointer; vertical-align: middle;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="1 4 1 10 7 10"></polyline>
                        <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
                    </svg>
                </button>`;
                document.getElementById('replay-btn').onclick = () => {
                    statusText.textContent = 'Tekrar dinleniyor...';
                    audioPlayer.currentTime = 0;
                    audioPlayer.play().catch(e => console.warn('Replay blocked:', e));
                    startProgress();
                };
            }
        }
    }, 80);
}

// =================== GUESS ===================
function handleGuess(btn, guess, correct) {
    if (!gameActive) return;
    gameActive = false;
    audioPlayer.pause();
    clearInterval(progressInterval);

    const isCorrect = guess === correct;
    results.push({ correct: isCorrect, trackName: correct, userAnswer: guess });
    updateTracker(currentIndex, isCorrect);

    // Tüm butonları kilitle
    const allBtns = optionsContainer.querySelectorAll('.option-btn');
    allBtns.forEach(b => { b.disabled = true; });

    if (isCorrect) {
        btn.classList.add('correct');
        statusText.textContent = 'Doğru!';
    } else {
        btn.classList.add('wrong');
        allBtns.forEach(b => { if (b.textContent === correct) b.classList.add('correct'); });
        statusText.textContent = 'Yanlış!';
    }

    // Son soru mu?
    if (currentIndex >= questions.length - 1) {
        setTimeout(showResults, 1200);
    } else {
        nextBtn.classList.remove('hidden');
    }
}

// =================== NEXT QUESTION ===================
nextBtn.onclick = () => {
    currentIndex++;
    if (currentIndex < questions.length) {
        loadQuestion(currentIndex);
    } else {
        showResults();
    }
};

// =================== RESULTS ===================
function showResults() {
    gameScreen.classList.add('hidden');
    resultScreen.classList.remove('hidden');

    const correctCount = results.filter(r => r.correct).length;
    const wrongCount = results.length - correctCount;
    const pct = Math.round((correctCount / results.length) * 100);

    document.getElementById('correct-count').textContent = correctCount;
    document.getElementById('wrong-count').textContent = wrongCount;

    // İkon ve başlık (SVG)
    const ICONS = {
        perfect: `<svg viewBox="0 0 24 24" fill="none" stroke="#1DB954" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
        great: `<svg viewBox="0 0 24 24" fill="none" stroke="#1DB954" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
        good: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
        meh: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="8" y1="15" x2="16" y2="15"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>`,
        bad: `<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`
    };
    let iconKey, title;
    if (pct === 100) { iconKey = 'perfect'; title = 'Mükemmel! Efsanesin!'; }
    else if (pct >= 80) { iconKey = 'great'; title = 'Harika! Çok iyisin!'; }
    else if (pct >= 60) { iconKey = 'good'; title = 'Fena değil!'; }
    else if (pct >= 40) { iconKey = 'meh'; title = 'Biraz daha pratik yap!'; }
    else { iconKey = 'bad'; title = 'Zor geldi galiba!'; }

    document.getElementById('result-emoji').innerHTML = ICONS[iconKey];
    document.getElementById('result-title').textContent = title;
    document.getElementById('result-subtitle').textContent = `${results.length} sorudan ${correctCount} doğru — %${pct}`;

    // Sanatçının notunu oku butonu
    const showNoteBtn = document.getElementById('show-note-btn');
    // Eğer buton disabled kaldıysa aktif hale getirelim (yeni oyun case'i için)
    showNoteBtn.disabled = false;

    showNoteBtn.onclick = () => {
        showNoteBtn.disabled = true;

        // Spotlight Overlay & Floating Note (AI Evaluation)
        const existingOverlay = document.getElementById('note-overlay');
        if (existingOverlay) existingOverlay.remove();

        const overlay = document.createElement('div');
        overlay.id = 'note-overlay';
        overlay.className = 'spotlight-overlay';

        // Geçici Spotlight Text
        const spotlightText = document.createElement('div');
        spotlightText.className = 'spotlight-text';
        spotlightText.innerHTML = `✨ ${selectedArtist.name} stüdyodan sana bir not iletiyor...`;

        overlay.appendChild(spotlightText);
        document.body.appendChild(overlay);

        // Hemen overlay'i görünür yap (Fade-in Spotlight)
        setTimeout(() => overlay.classList.add('visible'), 50);

        // Organik El Yazısı Efekti (Mürekkep)
        function handwritingEffect(text, element) {
            element.innerHTML = ''; // Temizle

            // Cümleyi kelimelere böl (boşluklardan)
            const words = text.split(' ');

            words.forEach((word, index) => {
                // Her kelime için kırılmayı önleyen ana span oluştur
                const wordSpan = document.createElement('span');
                wordSpan.className = 'ink-word';

                // Kelimenin her harfi için ink-letter span'i ekle
                const chars = word.split('');
                chars.forEach(char => {
                    const letterSpan = document.createElement('span');
                    letterSpan.className = 'ink-letter';
                    letterSpan.textContent = char;
                    wordSpan.appendChild(letterSpan);
                });

                element.appendChild(wordSpan);

                // Son kelime değilse araya normal boşluk karakteri ekle
                if (index < words.length - 1) {
                    element.appendChild(document.createTextNode(' '));
                }
            });

            const letterSpans = element.querySelectorAll('.ink-letter');
            let i = 0;

            // Akıcı animasyon için recursive setTimeout
            function pourInk() {
                if (i < letterSpans.length) {
                    letterSpans[i].classList.add('visible');
                    i++;
                    setTimeout(pourInk, 30); // Ne kadar küçük olursa o kadar hızlı ve su gibi akar
                }
            }

            // Küçük bir gecikme ile efekt başlasın
            setTimeout(pourInk, 100);
        }

        // Modal İçeriğini Oluşturma Fonksiyonu
        const renderModal = (message) => {
            overlay.innerHTML = `
                <div class="note-card" id="note-card-el" style="display: none;">
                    <button class="note-close-btn" id="note-close-btn">&times;</button>
                    <div class="note-title">${selectedArtist.name} SANA BİR NOT BIRAKTI</div>
                    <div class="note-text" id="note-text"></div>
                    <button class="note-close-action-btn" id="note-close-action-btn">Kapat</button>
                </div>
            `;

            const noteCardEl = document.getElementById('note-card-el');
            const noteTextEl = document.getElementById('note-text');
            const closeBtn = document.getElementById('note-close-btn');
            const closeActionBtn = document.getElementById('note-close-action-btn');

            noteCardEl.style.display = 'block';

            const closeHandler = () => {
                overlay.classList.remove('visible');
                setTimeout(() => overlay.remove(), 500); // Wait for transition
                showNoteBtn.disabled = false;
            };

            closeBtn.onclick = closeHandler;
            closeActionBtn.onclick = closeHandler;

            setTimeout(() => handwritingEffect(message, noteTextEl), 400);
        };

        // Cache kontrolü
        if (currentArtistNote) {
            // Önceden bir not var ise direkt render et
            renderModal(currentArtistNote);
        } else {
            // AI Değerlendirmesini Getir
            fetch(`${API_BASE}/evaluate?artist_name=${encodeURIComponent(selectedArtist.name)}&correct_count=${correctCount}&total_count=${results.length}`)
                .then(res => res.json())
                .then(data => {
                    currentArtistNote = data.message; // Gelen notu cache'e kaydet
                    renderModal(data.message);
                })
                .catch(err => {
                    console.error('AI Eval Error:', err);
                    // Hata durumunda kapatıyoruz
                    overlay.classList.remove('visible');
                    setTimeout(() => overlay.remove(), 500);
                    showNoteBtn.disabled = false;
                });
        }
    };

    // Cevap özeti
    const summaryEl = document.getElementById('answer-summary');
    summaryEl.innerHTML = '';
    results.forEach((r, i) => {
        const row = document.createElement('div');
        row.className = `summary-row ${r.correct ? 'summary-correct' : 'summary-wrong'}`;
        row.innerHTML = `
            <span class="summary-num">${i + 1}</span>
            <span class="summary-track">${r.trackName}</span>
            <span class="summary-icon ${r.correct ? 'icon-correct' : 'icon-wrong'}"></span>`;
        summaryEl.appendChild(row);
    });
}

// =================== PLAY AGAIN ===================
playAgainBtn.onclick = () => {
    resultScreen.classList.add('hidden');
    setupScreen.classList.remove('hidden');
    searchInput.value = '';
    startBtn.textContent = 'Oyunu Başlat';
    startBtn.disabled = true;
    selectedArtist = null;
    questions = [];
    results = [];
    currentIndex = 0;
    currentArtistNote = null;
};

// =================== LUCKY BUTTON ===================
const luckyBtn = document.getElementById('lucky-btn');

luckyBtn.onclick = async () => {
    // Rastgele sanatçı seç
    const artist = POPULAR_ARTISTS[Math.floor(Math.random() * POPULAR_ARTISTS.length)];

    // Animasyon: isim değiştirme efekti
    luckyBtn.classList.add('spinning');
    luckyBtn.disabled = true;

    const shuffleNames = [...POPULAR_ARTISTS].sort(() => Math.random() - 0.5);
    let i = 0;
    const ticker = setInterval(() => {
        searchInput.value = shuffleNames[i % shuffleNames.length].name;
        i++;
    }, 80);

    // 1 saniye sonra seçimi sabitle ve oyunu başlat
    await new Promise(r => setTimeout(r, 1000));
    clearInterval(ticker);
    luckyBtn.classList.remove('spinning');
    luckyBtn.disabled = false;

    selectArtist(artist);
    searchInput.value = artist.name;

    // Kısa bir bekleme sonrası otomatik başlat
    await new Promise(r => setTimeout(r, 300));
    startGame();
};
