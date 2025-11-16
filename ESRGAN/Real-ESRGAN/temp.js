// ==UserScript==
// @name         Civitai All-in-One: Auto Batch Generate & Local Autocomplete
// @namespace    http://tampermonkey.net/
// @version      2.3.3
// @description  FIXED: Intelligent batch generation that waits for prompt evaluation and skips non-safe prompts. Plus all original features.
// @author       ChatGPT & BEM (Fixed by Mentorbot)
// @match        https://civitai.com/*
// @grant        GM.xmlHttpRequest
// @license      MIT
// ==/UserScript==

(function() {
    'use strict';

    // --- SHARED CONFIG & ELEMENTS ---
    const PROMPT_TEXTAREA_ID = 'input_prompt';
    const DEBOUNCE_DELAY_MS = 50;

    // --- AUTOCOMPLETE CONFIG ---
    const LOCAL_TAGS_CSV_URL = 'https://gist.githubusercontent.com/bem13/0bc5091819f0594c53f0d96972c8b6ff/raw/b0aacd5ea4634ed4a9f320d344cc1fe81a60db5a/danbooru_tags_post_count.csv';
    const MAX_SUGGESTIONS_TO_SHOW = 10;

    // --- MY SUGGESTIONS CONFIG ---
    const MY_TAGS = {
        "S-Tier": [
            "Hyuuga_hinata", "Tier_harribel", "Papi_(monster_musume)", "Nijou_aki", "Matsumoto_rangiku", "Rem_galeu", "Rimuru_tempest", "Aqua_(konosuba)", "Oosuki_mamako", "Cattleya_(queen's_blade)", "Yumi (senran_kagura)"
        ],
        "A-Tier": [
            "Nami_(one_piece)","hasshaku-sama", "Boa_hancock", "Himejima_akeno", "Mikasa_ackerman", "Yor_briar", "Kuroka (high_school_dxd)", "Kashiwazaki_sena", "Daki_(kimetsu_no_yaiba)", "Busujima_saeko", "Sylvie (isekai_maou)", "Uzaki_hana", "Asada_shino", "Wiz_(konosuba)", "Sylpha_langlis", "Astraea (sora no otoshimono)", "Nymph (sora no otoshimono)", "Ikaros", "Esdeath", "Toujou_koneko"
        ],
        "B-Tier": [
            "Raynare", "Takamine_takane", "Anya (spy_x_family)", "Xenovia_quarta", "Rossweisse", "Nico_robin", "Yamanaka_ino", "Yue (arifureta)", "Haruno_sakura", "Milim_nava", "Uzaki_tsuki", "Shion_(tensei_shitara_slime_datta_ken)", "Mavis_vermilion", "Nelliel_tu_odelschwanck", "Elina (queen's_blade)", "Lucy_heartfilia", "Yuigahama_yui", "Erza_scarlet", "Juvia_lockser", "Darkness_(konosuba)", "Grayfia_lucifuge", "Yaoyorozu_momo", "Ghislaine_dedoldia", "Totsuka_saika", "Tomoe (queen's_blade)", "Rias_gremory"
        ],
        "C-Tier": [
            "Nefertari_vivi", "Roxanne (isekai_meikyuu_de_harem_wo)", "Leina (queen's_blade)", "Shidou_irina", "Nakiri_erina", "Albedo_(overlord)", "Chloe_von_einzbern", "Inoue_orihime", "Nagatoro_hayase", "Yukinoshita_yukino", "Akame_(akame_ga_kill!)", "Shalltear_bloodfallen", "Yamato_(one_piece)"
        ],
        "D-Tier": [
            "Mitarashi_anko", "Echidna (queen's_blade)", "Shuna (tensura)", "Melona (queen's_blade)", "Kitagawa_marin", "Tamaki_kotatsu", "Maki_oze"],
        "Shota": [
            "1boy", "mature_female", "breast_rest", "height_difference", "large_breasts", "tall_female", "safe_neg", "1girl", "small penis", "short male", "femdom", "Age_difference", "size difference" ],
        "Clothing": [ "hoodie", "denim_shorts", "loincloth", "nightgown", "sheer_fabric", "backless_outfit", "lingerie", "babydoll", "bodystocking", "bikini", "bikini_bottom_only", "bikini_top_only", "g-string", "thong", "costume" ],
        "Details_Focus": [ "plunging_neckline", "cleavage", "collarbone", "arm_between_breasts", "backboob", "nipple_slip", "covered_erect_nipples", "covered_navel", "ear_focus", "stomach", "soles", "toes", "feet", "shoulders", "armpit_focus", "back_focus", "breast_focus", "ass_focus", "foot_focus" ],
        "Background_Location": [ "detailed_background", "locker_room", "bathroom", "bathtub", "fitting_room", "closet", "gym_storeroom" ],
        "Composition_Camera": [ "close-up", "full_body", "feet_out_of_frame", "zoom_out", "rear_shotpov", "perspective", "depth_of_field", "pincushion_distortion", "motion_blur:1.1", "motion_lines:1.1", "polarized" ],
        "Subject_Persona": [ "1girl", "2boys", "young_lady", "woman", "mature_female", "mature", "adorable", "feminine", "sensual", "sassy", "sexy", "athletic", "cute", "african", "european", "dark_elf", "wolf_ears", "slime (creature)" ],
        "Appearance_Face": [ "aqua_hair", "wet", "sweat", "saliva trail", "saliva", "shiny skin", "single_hair_bun", "very_long_hair", "antenna_hair", "perfect_lips", "one_eye_closed", "open_mouth", "parted_lips", "blush", "sleepy", "disdain", "kubrick_stare", "colored_eyelashes", "perfect_face", "hourglass_figure", "perfect_breasts", "medium_breasts", "perfect_anatomy_hands", "perfect_anatomy_fingers", "fingernails", "muscular", "abs", "adam's_apple", "biceps", "obliques", "giantess" ],
        "Pose": [ "breast_smother", "breast_feeding", "aftersex", "grabbing_from_behind", "grabbing_another's_breast", "groping", "thigh_sex", "buttjob", "nursing_handjob", "one_leg_lock", "spooning", "prone_bone", "missionary", "suspended_congress", "upright_straddle", "amazon_position", "full_nelson", "reverse_spitroast", "paizuri" ],
        "Quality_Details": [ "masterpiece", "best_quality", "high_quality", "amazing_quality", "highly_detailed", "ultra-detailed", "score_9", "score_8_up", "score_7_up", "absurdres", "highres", "4K", "8K", "UHD", "HDR", "sharp_focus", "sharp_details", "vivid_color" ],
        "Art_Style_Realistic": [ "photorealistic", "photo (medium)", "cinematic_lighting", "chiaroscuro", "impasto", "intrinsic_light", "luster", "shiny_color", "strong_coloring", "masterful_shading" ],
        "Art_Style_Anime": [ "anime_screencap", "anime_screenshot", "anime_coloring", "source_anime", "key_visual", "official_art", "promotional_art", "anime_style" ]
    };


    // --- CUSTOM BUTTON CONFIG ---
    const ORIGINAL_GENERATE_BUTTON_SELECTOR = 'button[data-tour="gen:submit"]';
    const PROMPT_SEPARATOR = '###';
    const MY_BUTTON_SETTINGS = {
        defaultText: '🚀',
        batchModeTextColor: '#FFFFFF',
        defaultBackgroundColor: 'rgba(97, 6, 212, 0.85)',
        batchModeBackgroundColor: 'rgba(212, 6, 97, 0.85)',
        width: '65px',
        height: '65px',
        bottom: '20px',
        right: '20px',
        fontSize: '32px',
        zIndex: 99999,
    };
    const CANCEL_BUTTON_SETTINGS = {
        text: '❌',
        fontSize: '20px',
        zIndex: 100000,
    };

    // --- SHARED INTERNAL VARIABLES ---
    let promptInput = null;
    let debounceTimer;

    // --- AUTOCOMPLETE INTERNAL VARIABLES ---
    let allLocalTags = [];
    let suggestionsBox = null;
    let currentSuggestions = [];
    let selectedSuggestionIndex = -1;

    // --- MY SUGGESTIONS INTERNAL VARIABLES ---
    let mySuggestionsModal = null;
    let selectedCustomTags = new Set();

    // --- CUSTOM BUTTON INTERNAL VARIABLES ---
    let promptQueue = [];
    let currentPromptIndex = 0;
    let isInBatchMode = false;
    let myButton = null;
    let cancelButton = null;
    let generateButtonObserver = null;

    // --- SHARED STYLES & FUNCTIONS ---

    // Style Injection
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        #simple-autocomplete-suggestions-box {
            position: fixed; background-color: #1a1b1e; border: 1px solid #333; border-radius: 5px;
            z-index: 99999; overflow-y: auto; max-height: 150px; padding: 2px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.5); left: 50%; transform: translateX(-50%);
            width: 95%; max-width: 600px;
        }
        #simple-autocomplete-suggestions-box div {
            padding: 6px 10px; cursor: pointer; white-space: nowrap; overflow: hidden;
            text-overflow: ellipsis; color: #C1C2C5; font-size: 15px;
        }
        #simple-autocomplete-suggestions-box div:hover { background-color: #282a2d; }
        .simple-autocomplete-selected { background-color: #383a3e; }
        .simple-suggestion-count {
            color: #98C379; font-weight: normal; margin-left: 8px; font-size: 0.9em;
        }
        #my-suggestions-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0, 0, 0, 0.7); display: none;
            align-items: center; justify-content: center; z-index: 100001;
        }
        #my-suggestions-modal {
            background-color: #1a1b1e; border: 1px solid #444; border-radius: 8px;
            width: 90%; max-width: 800px; max-height: 85vh;
            display: flex; flex-direction: column; box-shadow: 0 5px 20px rgba(0,0,0,0.5);
        }
        .my-suggestions-header {
            padding: 10px 15px; border-bottom: 1px solid #333; display: flex;
            justify-content: space-between; align-items: center;
        }
        .my-suggestions-header h3 { margin: 0; color: #E0E1E2; font-size: 18px; }
        .my-suggestions-close-btn {
            background: none; border: none; color: #E0E1E2; font-size: 24px;
            cursor: pointer; padding: 0 5px;
        }
        .my-suggestions-content { padding: 10px; overflow-y: auto; }
        .my-suggestions-global-actions {
            background-color: #2c2f33; padding: 10px; border-radius: 5px; margin-bottom: 10px;
            display: flex; align-items: center; justify-content: space-between; gap: 10px;
            font-size: 14px; color: #E0E1E2;
        }
        .my-suggestions-global-actions input[type="number"] {
            width: 60px; background-color: #1a1b1e; color: #E0E1E2; border: 1px solid #444;
            border-radius: 4px; padding: 4px; text-align: center;
        }
        .my-suggestions-global-actions button {
            background-color: #5865F2; color: white; border: none; border-radius: 4px;
            padding: 5px 12px; cursor: pointer; font-weight: bold;
        }
        .my-suggestions-category { margin-bottom: 10px; }
        .my-suggestions-category-header {
            background-color: #282a2d; color: #98C379; padding: 8px 12px;
            border-radius: 4px; cursor: pointer; font-weight: bold;
            display: flex; align-items: center; justify-content: space-between;
        }
        .my-suggestions-category-header .category-title-section {
            display: flex; align-items: center; gap: 10px; flex-grow: 1;
        }
        .my-suggestions-category-header .category-title { flex-grow: 1; }
        .my-suggestions-category-actions { display: flex; gap: 8px; }
        .my-suggestions-category-action-btn {
            background-color: #4f545c; color: #dcddde; border: none; padding: 2px 8px;
            font-size: 12px; border-radius: 3px; cursor: pointer;
        }
        .my-suggestions-tags-container {
            padding-left: 15px; max-height: 0; overflow: hidden; transition: max-height 0.3s ease;
        }
        .my-suggestions-tags-container.open {
            max-height: 400px;
            overflow-y: auto;
        }
        .my-suggestions-tag-item {
            display: flex; align-items: center; padding: 6px 0; color: #C1C2C5;
        }
        .my-suggestions-tag-item input[type="checkbox"] { margin-right: 10px; cursor: pointer; }
        .my-suggestions-tag-item .tag-name { flex-grow: 1; cursor: pointer; }
        .my-suggestions-tag-item .tag-name:hover { color: #FFFFFF; }
        .my-suggestions-actions {
            padding: 10px 15px; border-top: 1px solid #333; display: none;
            gap: 10px; justify-content: flex-end;
        }
        .my-suggestions-action-btn {
            padding: 8px 15px; border-radius: 5px; border: none; cursor: pointer;
            font-weight: bold; color: white;
        }
        .paste-together-btn { background-color: #2a75d2; }
        .paste-separately-btn { background-color: #d22a61; }
        .my-suggestions-special-button { font-weight: bold; color: #E5C07B; }
    `;
    document.head.appendChild(styleElement);

    // Debugging Helper
    function debug(msg) { console.log([Civitai AIO] ${msg}); }

    // Function to set value and dispatch input event (for React compatibility)
    function setNativeValue(element, value) { const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set; const prototype = Object.getPrototypeOf(element); const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set; if (valueSetter && valueSetter !== prototypeValueSetter) { prototypeValueSetter.call(element, value); } else { valueSetter.call(element, value); } element.dispatchEvent(new Event('input', { bubbles: true })); }


    // --- AUTOCOMPLETE FUNCTIONS ---
    async function loadTagsFromCSV() { debug('Attempting to load tags from CSV...'); return new Promise((resolve, reject) => { GM.xmlHttpRequest({ method: 'GET', url: LOCAL_TAGS_CSV_URL, onload: function(response) { if (response.status === 200) { try { const lines = response.responseText.split('\n'); const parsedTags = lines.map(line => { const parts = line.split(','); if (parts.length === 2) { const label = parts[0].trim(); const post_count = parseInt(parts[1].trim(), 10); if (label && !isNaN(post_count)) { return { label: label, count: post_count }; } } return null; }).filter(tag => tag !== null); allLocalTags = parsedTags; debug(Successfully loaded and parsed ${allLocalTags.length} tags.); resolve(); } catch (e) { console.error("Error parsing local tags CSV:", e); reject(e); } } else { console.error("Failed to load local tags CSV:", response.status, response.statusText); reject(new Error(Failed to load local tags: ${response.status} ${response.statusText})); } }, onerror: function(error) { console.error("Local tags CSV request error:", error); reject(error); } }); }); }
    function getCurrentWord(text, cursorPosition) { if (cursorPosition === undefined) cursorPosition = text.length; const textBeforeCursor = text.substring(0, cursorPosition); const lastCommaIndex = textBeforeCursor.lastIndexOf(','); let startPos, word; if (lastCommaIndex !== -1) { startPos = lastCommaIndex + 1; word = textBeforeCursor.substring(startPos).trim(); if (word) { const leadingSpaces = textBeforeCursor.substring(startPos).length - textBeforeCursor.substring(startPos).trimLeft().length; startPos = startPos + leadingSpaces; } } else { startPos = 0; word = textBeforeCursor.trim(); if (word && textBeforeCursor !== word) { startPos = textBeforeCursor.indexOf(word); } } return { word, startPos }; }
    function fetchSuggestions(term) { if (!term || allLocalTags.length === 0) { clearSuggestions(); showSuggestions(term); return; } clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { const lowerCaseTerm = term.toLowerCase(); const filtered = allLocalTags.filter(tag => tag.label.toLowerCase().startsWith(lowerCaseTerm)).slice(0, MAX_SUGGESTIONS_TO_SHOW); currentSuggestions = filtered; showSuggestions(term); }, DEBOUNCE_DELAY_MS); }

    function showSuggestions(term) {
        if (!suggestionsBox || !document.body.contains(suggestionsBox)) {
            createSuggestionsBox();
            if (!suggestionsBox) return;
        }

        const shouldShow = currentSuggestions.length > 0 || (promptInput && document.activeElement === promptInput);
        if (!shouldShow) {
            clearSuggestions();
            return;
        }

        suggestionsBox.innerHTML = '';

        const mySuggestionsButton = document.createElement('div');
        mySuggestionsButton.innerHTML = My Suggestions ⭐;
        mySuggestionsButton.className = 'my-suggestions-special-button';
        mySuggestionsButton.addEventListener('click', openMySuggestionsModal);
        suggestionsBox.appendChild(mySuggestionsButton);

        currentSuggestions.forEach(suggestion => {
            const suggestionDiv = document.createElement('div');
            suggestionDiv.innerHTML = ${suggestion.label} <span class="simple-suggestion-count">[${suggestion.count}]</span>;
            suggestionDiv.addEventListener('click', () => insertSuggestion(suggestion.label));
            suggestionsBox.appendChild(suggestionDiv);
        });

        suggestionsBox.style.display = 'block';
        selectedSuggestionIndex = -1;
        updateSuggestionsBoxPosition();
    }

    function clearSuggestions() { if (suggestionsBox) { suggestionsBox.style.display = 'none'; suggestionsBox.innerHTML = ''; } currentSuggestions = []; selectedSuggestionIndex = -1; }
    function insertSuggestion(suggestion) { if (!promptInput) return; const currentText = promptInput.value; const cursorPosition = promptInput.selectionStart; const { startPos } = getCurrentWord(currentText, cursorPosition); const textBeforeWord = currentText.substring(0, startPos); const textAfterWord = currentText.substring(cursorPosition); let newText = textBeforeWord + suggestion + ', ' + textAfterWord; if (currentText.trim() === '') newText = suggestion + ', '; const newCursorPosition = textBeforeWord.length + suggestion.length + 2; setNativeValue(promptInput, newText); promptInput.setSelectionRange(newCursorPosition, newCursorPosition); clearSuggestions(); promptInput.focus(); }

    // START: MODIFIED SECTION - إصلاح مشكلة السطر الجديد (Enter key)
    function handleACKeyDown(e) {
        if (e.target !== promptInput || !suggestionsBox || suggestionsBox.style.display !== 'block') {
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
            case 'ArrowUp':
                // Prevent cursor from moving in the textarea
                e.preventDefault();
                e.stopImmediatePropagation();
                if (e.key === 'ArrowDown') {
                    selectedSuggestionIndex = Math.min(selectedSuggestionIndex + 1, suggestionsBox.children.length - 1);
                } else { // ArrowUp
                    selectedSuggestionIndex = Math.max(selectedSuggestionIndex - 1, -1);
                }
                updateSuggestionSelection();
                break;

            case 'Enter':
            case 'Tab':
                // This is the key logic:
                // We ONLY prevent the default action (like creating a newline) if we are actively selecting a suggestion.
                // A suggestion is "active" if it's highlighted with arrow keys (selectedSuggestionIndex != -1)
                // or if there are suggestions visible and the user hits Enter (to select the first one).
                if (selectedSuggestionIndex !== -1 || (e.key === 'Enter' && currentSuggestions.length > 0)) {
                    e.preventDefault();
                    e.stopImmediatePropagation();

                    if (selectedSuggestionIndex !== -1) {
                        // A specific item is highlighted, click it
                        suggestionsBox.children[selectedSuggestionIndex].click();
                    } else {
                        // No highlight, but Enter was pressed with suggestions visible. Click the first actual tag.
                        // We check for length > 1 because child 0 is our "My Suggestions" button.
                        if (suggestionsBox.children.length > 1) {
                           suggestionsBox.children[1].click();
                        }
                    }
                }
                // IF THE CONDITIONS ABOVE ARE NOT MET:
                // The function does nothing, allowing the 'Enter' key to perform its default action, which is creating a new line.
                break;

            case 'Escape':
                e.preventDefault();
                e.stopImmediatePropagation();
                clearSuggestions();
                break;

            default:
                // For any other key (like letters, numbers, etc.), do nothing and let the browser handle it.
                return;
        }
    }
    // END: MODIFIED SECTION

    function updateSuggestionSelection() { if (!suggestionsBox) return; const suggestionDivs = suggestionsBox.querySelectorAll('div'); suggestionDivs.forEach((div, index) => { div.classList.toggle('simple-autocomplete-selected', index === selectedSuggestionIndex); if (index === selectedSuggestionIndex) div.scrollIntoView({ block: 'nearest' }); }); }
    function updateSuggestionsBoxPosition() { if (!promptInput || !suggestionsBox || suggestionsBox.style.display === 'none') return; const inputRect = promptInput.getBoundingClientRect(); const viewportHeight = window.innerHeight || document.documentElement.clientHeight; const viewportWidth = window.innerWidth || document.documentElement.clientWidth; let left = inputRect.left; let width = inputRect.width; if (left + width > viewportWidth - 10) width = viewportWidth - left - 10; if (left < 10) { width += left - 10; left = 10; } suggestionsBox.style.position = 'fixed'; suggestionsBox.style.left = ${left}px; suggestionsBox.style.width = ${width}px; suggestionsBox.style.transform = 'none'; const boxHeight = suggestionsBox.offsetHeight; if (inputRect.bottom + boxHeight > viewportHeight && inputRect.top - boxHeight > 0) { suggestionsBox.style.top = ${inputRect.top - boxHeight}px; } else { suggestionsBox.style.top = ${inputRect.bottom}px; } }
    function createSuggestionsBox() { if (!suggestionsBox || !document.body.contains(suggestionsBox)) { suggestionsBox = document.createElement('div'); suggestionsBox.id = 'simple-autocomplete-suggestions-box'; suggestionsBox.style.display = 'none'; document.body.appendChild(suggestionsBox); debug('Suggestions box created/re-appended.'); } }
    function handleInputEvent(e) { const currentWordObj = getCurrentWord(promptInput.value, promptInput.selectionStart); fetchSuggestions(currentWordObj.word); }
    function handleClickOutside(e) { if (suggestionsBox && !suggestionsBox.contains(e.target) && promptInput && !promptInput.contains(e.target)) { clearSuggestions(); } }

    // --- MY SUGGESTIONS FUNCTIONS ---
    function createMySuggestionsModal() {
        if (mySuggestionsModal && document.body.contains(mySuggestionsModal)) return;
        const overlay = document.createElement('div');
        overlay.id = 'my-suggestions-overlay';
        const modal = document.createElement('div');
        modal.id = 'my-suggestions-modal';
        const header = document.createElement('div');
        header.className = 'my-suggestions-header';
        const title = document.createElement('h3');
        title.textContent = 'My Personal Suggestions';
        const closeBtn = document.createElement('button');
        closeBtn.className = 'my-suggestions-close-btn';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = closeMySuggestionsModal;
        header.appendChild(title);
        header.appendChild(closeBtn);
        const content = document.createElement('div');
        content.className = 'my-suggestions-content';
        const globalActions = document.createElement('div');
        globalActions.className = 'my-suggestions-global-actions';
        globalActions.innerHTML = `
            <span>تحديد عشوائي من المجلدات المحددة:</span>
            <input type="number" id="global-random-count" value="2" min="1">
            <button id="global-random-btn">اختر</button>
        `;
        const actions = document.createElement('div');
        actions.className = 'my-suggestions-actions';
        const pasteTogetherBtn = document.createElement('button');
        pasteTogetherBtn.className = 'my-suggestions-action-btn paste-together-btn';
        pasteTogetherBtn.textContent = 'Paste Together';
        pasteTogetherBtn.onclick = handlePasteTogether;
        const pasteSeparatelyBtn = document.createElement('button');
        pasteSeparatelyBtn.className = 'my-suggestions-action-btn paste-separately-btn';
        pasteSeparatelyBtn.textContent = 'Paste Separately';
        pasteSeparatelyBtn.onclick = handlePasteSeparately;
        actions.appendChild(pasteTogetherBtn);
        actions.appendChild(pasteSeparatelyBtn);
        modal.appendChild(header);
        content.appendChild(globalActions);
        modal.appendChild(content);
        modal.appendChild(actions);
        overlay.appendChild(modal);
        mySuggestionsModal = overlay;
        document.body.appendChild(mySuggestionsModal);
        mySuggestionsModal.querySelector('#global-random-btn').addEventListener('click', handleGlobalRandomSelect);
        renderMySuggestionsContent();
    }

    function renderMySuggestionsContent() {
        const contentArea = mySuggestionsModal.querySelector('.my-suggestions-content');
        contentArea.querySelectorAll('.my-suggestions-category').forEach(el => el.remove());
        for (const category in MY_TAGS) {
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'my-suggestions-category';
            const header = document.createElement('div');
            header.className = 'my-suggestions-category-header';
            const titleSection = document.createElement('div');
            titleSection.className = 'category-title-section';
            const categoryCheckbox = document.createElement('input');
            categoryCheckbox.type = 'checkbox';
            categoryCheckbox.title = 'Select this category for global random selection';
            categoryCheckbox.dataset.category = category;
            const title = document.createElement('span');
            title.className = 'category-title';
            title.textContent = category;
            const tagsContainer = document.createElement('div');
            tagsContainer.className = 'my-suggestions-tags-container';
            titleSection.appendChild(categoryCheckbox);
            titleSection.appendChild(title);
            titleSection.onclick = (e) => {
                if (e.target.type !== 'checkbox') {
                    tagsContainer.classList.toggle('open');
                }
            };
            const categoryActions = document.createElement('div');
            categoryActions.className = 'my-suggestions-category-actions';
            const selectAllBtn = document.createElement('button');
            selectAllBtn.className = 'my-suggestions-category-action-btn';
            selectAllBtn.textContent = 'تحديد الكل';
            selectAllBtn.onclick = (e) => {
                e.stopPropagation();
                handleSelectAllInCategory(category, tagsContainer, selectAllBtn);
            };
            const randomBtn = document.createElement('button');
            randomBtn.className = 'my-suggestions-category-action-btn';
            randomBtn.textContent = 'عشوائي (+2)';
            randomBtn.onclick = (e) => {
                e.stopPropagation();
                handleRandomSelectInCategory(category, tagsContainer);
            };
            categoryActions.appendChild(selectAllBtn);
            categoryActions.appendChild(randomBtn);
            header.appendChild(titleSection);
            header.appendChild(categoryActions);
            MY_TAGS[category].forEach(tag => {
                const item = document.createElement('div');
                item.className = 'my-suggestions-tag-item';
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.dataset.tag = tag;
                checkbox.onchange = () => handleCustomTagCheckboxChange(tag, checkbox.checked);
                const name = document.createElement('span');
                name.className = 'tag-name';
                name.textContent = tag.replace(/_/g, ' ');
                name.onclick = () => handleCustomTagNameClick(tag);
                item.appendChild(checkbox);
                item.appendChild(name);
                tagsContainer.appendChild(item);
            });
            categoryDiv.appendChild(header);
            categoryDiv.appendChild(tagsContainer);
            contentArea.appendChild(categoryDiv);
        }
    }

    function openMySuggestionsModal() {
        if (!mySuggestionsModal) createMySuggestionsModal();
        clearSuggestions();
        selectedCustomTags.clear();
        mySuggestionsModal.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        mySuggestionsModal.querySelectorAll('.my-suggestions-category-action-btn').forEach(btn => {
            if (btn.textContent.includes('إلغاء')) btn.textContent = 'تحديد الكل';
        });
        updateMySuggestionsActions();
        mySuggestionsModal.style.display = 'flex';
    }

    function closeMySuggestionsModal() { if (mySuggestionsModal) mySuggestionsModal.style.display = 'none'; }
    function handleCustomTagCheckboxChange(tag, isChecked) { if (isChecked) { selectedCustomTags.add(tag); } else { selectedCustomTags.delete(tag); } updateMySuggestionsActions(); }
    function handleCustomTagNameClick(tag) { insertSuggestion(tag); closeMySuggestionsModal(); }
    function updateMySuggestionsActions() { const actionsDiv = mySuggestionsModal.querySelector('.my-suggestions-actions'); actionsDiv.style.display = selectedCustomTags.size > 0 ? 'flex' : 'none'; }
    function handlePasteTogether() { if (selectedCustomTags.size === 0 || !promptInput) return; const tagsToInsert = Array.from(selectedCustomTags).join(', '); const currentPrompt = promptInput.value.trim(); const separator = currentPrompt && !currentPrompt.endsWith(',') ? ', ' : ''; const newPrompt = currentPrompt + separator + tagsToInsert; setNativeValue(promptInput, newPrompt); closeMySuggestionsModal(); promptInput.focus(); }
    function handlePasteSeparately() { if (selectedCustomTags.size === 0 || !promptInput) return; const basePrompt = promptInput.value.trim(); const newPrompts = Array.from(selectedCustomTags).map(tag => { return tag + (basePrompt ? ', ' + basePrompt : ''); }); const finalPromptText = newPrompts.join(\n${PROMPT_SEPARATOR}\n); setNativeValue(promptInput, finalPromptText); closeMySuggestionsModal(); setTimeout(handleCustomButtonClick, 100); }
    function handleSelectAllInCategory(categoryName, container, button) { const tagsInCategory = MY_TAGS[categoryName]; const checkboxes = container.querySelectorAll('input[type="checkbox"]'); const isSelectAllAction = button.textContent === 'تحديد الكل'; checkboxes.forEach((cb, index) => { const tag = tagsInCategory[index]; if (cb.checked !== isSelectAllAction) { cb.checked = isSelectAllAction; handleCustomTagCheckboxChange(tag, isSelectAllAction); } }); button.textContent = isSelectAllAction ? 'إلغاء الكل' : 'تحديد الكل'; }
    function handleRandomSelectInCategory(categoryName, container) { const tagsInCategory = MY_TAGS[categoryName]; const availableTags = tagsInCategory.filter(tag => !selectedCustomTags.has(tag)); if (availableTags.length === 0) { debug(No unselected tags left in ${categoryName}); return; } const shuffled = availableTags.sort(() => 0.5 - Math.random()); const tagsToSelect = shuffled.slice(0, 2); tagsToSelect.forEach(tag => { const checkbox = container.querySelector(input[data-tag="${tag}"]); if (checkbox && !checkbox.checked) { checkbox.checked = true; handleCustomTagCheckboxChange(tag, true); } }); }
    function handleGlobalRandomSelect() { const countInput = mySuggestionsModal.querySelector('#global-random-count'); const numToSelect = parseInt(countInput.value, 10); if (isNaN(numToSelect) || numToSelect <= 0) return; const selectedCategories = Array.from(mySuggestionsModal.querySelectorAll('.my-suggestions-category-header .category-title-section input[type="checkbox"]:checked')).map(cb => cb.dataset.category); if (selectedCategories.length === 0) { alert('الرجاء تحديد مجلد واحد على الأقل أولاً (عبر مربع الاختيار بجانب اسم المجلد).'); return; } let tagPool = []; selectedCategories.forEach(catName => { tagPool.push(...MY_TAGS[catName]); }); const availableTags = tagPool.filter(tag => !selectedCustomTags.has(tag)); const uniqueAvailableTags = [...new Set(availableTags)]; const shuffled = uniqueAvailableTags.sort(() => 0.5 - Math.random()); const tagsToSelect = shuffled.slice(0, numToSelect); tagsToSelect.forEach(tag => { const checkbox = mySuggestionsModal.querySelector(input[data-tag="${tag}"]); if (checkbox && !checkbox.checked) { checkbox.checked = true; handleCustomTagCheckboxChange(tag, true); } }); }

    // --- CUSTOM BUTTON FUNCTIONS ---
    function updateButtonDisplay() {
        if (!myButton) return;
        if (isInBatchMode) {
            cancelButton.style.display = 'flex';
            myButton.style.backgroundColor = MY_BUTTON_SETTINGS.batchModeBackgroundColor;
            // Corrected remaining count calculation
            const remaining = promptQueue.length - currentPromptIndex;
            if (remaining > 0) {
                myButton.innerText = ${remaining};
                myButton.setAttribute('title', Batch Mode: ${remaining} prompts left. Auto-generating...);
            } else {
                myButton.innerText = '✅';
                // Use a different function to end batch mode to avoid race conditions
            }
        } else {
            if (cancelButton) cancelButton.style.display = 'none';
            myButton.innerText = MY_BUTTON_SETTINGS.defaultText;
            myButton.style.backgroundColor = MY_BUTTON_SETTINGS.defaultBackgroundColor;
            myButton.setAttribute('title', 'Generate Image (Custom Button)');
        }
    }

    function exitBatchMode() { if (generateButtonObserver) { generateButtonObserver.disconnect(); debug('Generate button observer disconnected.'); } isInBatchMode = false; promptQueue = []; currentPromptIndex = 0; debug('Batch mode exited.'); updateButtonDisplay(); }
    function startBatchProcess() { if (!promptInput) { alert('Prompt textarea not found!'); return; } const fullPromptText = promptInput.value.trim(); if (!fullPromptText.includes(PROMPT_SEPARATOR)) { clickOriginalGenerateButton(); return; } const splitPrompts = fullPromptText.split(PROMPT_SEPARATOR).map(p => p.trim()).filter(p => p.length > 0); if (splitPrompts.length > 1) { isInBatchMode = true; promptQueue = splitPrompts; currentPromptIndex = 0; debug(Batch mode activated with ${promptQueue.length} prompts.); setNativeValue(promptInput, ''); updateButtonDisplay(); observeGenerateButton(); processNextBatchPrompt(); } else { clickOriginalGenerateButton(); } }
    function handleCustomButtonClick() { if (!isInBatchMode) { startBatchProcess(); } else { debug('Manual override detected, but batch is already running.'); } }
    function clickOriginalGenerateButton() { const originalButton = document.querySelector(ORIGINAL_GENERATE_BUTTON_SELECTOR); if (originalButton && !originalButton.disabled) { debug('Clicking original generate button...'); originalButton.click(); } else { alert('Original "Generate" button not found or not ready!'); if (isInBatchMode) exitBatchMode(); } }


    // =================================================================================
    // START: MODIFIED BATCH LOGIC
    // =================================================================================

    function processNextBatchPrompt() {
        if (!isInBatchMode || currentPromptIndex >= promptQueue.length) {
            // If the queue is finished, the observer will call exitBatchMode when the last image is done.
            if (isInBatchMode) {
                updateButtonDisplay(); // Show the checkmark
                setTimeout(exitBatchMode, 2000); // safety timeout
            }
            return;
        }

        const generateButton = document.querySelector(ORIGINAL_GENERATE_BUTTON_SELECTOR);
        if (!generateButton || generateButton.disabled) {
            debug('Generate button is busy or not found. Waiting for observer to trigger next action.');
            return;
        }

        const nextPrompt = promptQueue[currentPromptIndex];
        debug(Processing prompt ${currentPromptIndex + 1} of ${promptQueue.length});
        setNativeValue(promptInput, nextPrompt);

        // Instead of clicking immediately, we wait for the evaluation.
        setTimeout(checkPromptEvaluation, 500); // Wait half a second for evaluation to start
    }

    function checkPromptEvaluation() {
        const generateButton = document.querySelector(ORIGINAL_GENERATE_BUTTON_SELECTOR);
        if (!generateButton) {
            debug("Button disappeared during evaluation. Exiting batch mode.");
            exitBatchMode();
            return;
        }

        // If the button is disabled, it means the site is still evaluating the prompt. We wait.
        if (generateButton.disabled) {
            debug("Prompt is still being evaluated. Waiting...");
            setTimeout(checkPromptEvaluation, 500); // Check again in a bit
            return;
        }

        // Now the button is enabled. We can check its color.
        const buttonColor = getComputedStyle(generateButton).getPropertyValue('--button-bg').trim();
        const isSafeColor = buttonColor.includes('4dabf7'); // The hex code for the blue "safe" button

        currentPromptIndex++; // We advance the index here, regardless of outcome
        updateButtonDisplay();

        if (isSafeColor) {
            debug("Prompt evaluated as SAFE (blue). Clicking generate.");
            clickOriginalGenerateButton();
        } else {
            debug(Prompt evaluated as NON-SAFE (color: ${buttonColor}). SKIPPING this prompt.);
            // The observer will detect that the button is still enabled and will automatically call processNextBatchPrompt.
            // We can also call it directly for faster processing.
            setTimeout(processNextBatchPrompt, 200);
        }
    }

    function observeGenerateButton() {
        const targetNode = document.querySelector(ORIGINAL_GENERATE_BUTTON_SELECTOR);
        if (!targetNode) {
            debug('Could not find original generate button to observe. Will retry.');
            setTimeout(observeGenerateButton, 1000);
            return;
        }
        if (generateButtonObserver) {
            generateButtonObserver.disconnect();
        }

        const config = { attributes: true, attributeFilter: ['disabled'] };

        const callback = function(mutationsList, observer) {
            for (const mutation of mutationsList) {
                if (mutation.attributeName === 'disabled') {
                    const isBusy = targetNode.hasAttribute('disabled');
                    debug(Generate button "isBusy" state changed to: ${isBusy});
                    // The key change: We only proceed when the button becomes NOT busy.
                    if (!isBusy) {
                        setTimeout(processNextBatchPrompt, 500); // Wait a moment for UI to settle
                    }
                }
            }
        };
        generateButtonObserver = new MutationObserver(callback);
        generateButtonObserver.observe(targetNode, config);
        debug('Now observing the original generate button for "disabled" state changes.');
    }

    // =================================================================================
    // END: MODIFIED BATCH LOGIC
    // =================================================================================


    // --- INITIALIZATION ---
    function initializeFeatures() {
        promptInput = document.getElementById(PROMPT_TEXTAREA_ID);
        if (!promptInput) {
            debug('Prompt textarea not found yet. Deferring initialization.');
            return;
        }
        createSuggestionsBox();
        if (!promptInput.hasAcListeners) {
            promptInput.addEventListener('keydown', handleACKeyDown, true);
            promptInput.addEventListener('input', handleInputEvent);
            document.addEventListener('click', handleClickOutside);
            window.addEventListener('scroll', updateSuggestionsBoxPosition);
            window.addEventListener('resize', updateSuggestionsBoxPosition);
            promptInput.hasAcListeners = true;
            debug('Autocomplete listeners attached.');
        }
        createMySuggestionsModal();
        if (!myButton || !document.body.contains(myButton)) {
            myButton = document.createElement('div');
            Object.assign(myButton.style, {
                position: 'fixed', bottom: MY_BUTTON_SETTINGS.bottom, right: MY_BUTTON_SETTINGS.right,
                width: MY_BUTTON_SETTINGS.width, height: MY_BUTTON_SETTINGS.height,
                backgroundColor: MY_BUTTON_SETTINGS.defaultBackgroundColor, color: MY_BUTTON_SETTINGS.batchModeTextColor,
                borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: MY_BUTTON_SETTINGS.fontSize, zIndex: MY_BUTTON_SETTINGS.zIndex,
                cursor: 'pointer', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)', transition: 'all 0.2s ease',
            });
            myButton.innerText = MY_BUTTON_SETTINGS.defaultText;
            myButton.addEventListener('click', () => {
                myButton.style.transform = 'scale(0.95)';
                setTimeout(() => { myButton.style.transform = 'scale(1)'; }, 100);
                handleCustomButtonClick();
            });
            document.body.appendChild(myButton);
            cancelButton = document.createElement('div');
            Object.assign(cancelButton.style, {
                position: 'fixed', bottom: calc(${MY_BUTTON_SETTINGS.bottom} + ${MY_BUTTON_SETTINGS.height} - 10px),
                right: MY_BUTTON_SETTINGS.right, width: '30px', height: '30px', backgroundColor: '#333',
                color: 'white', borderRadius: '50%', display: 'none', alignItems: 'center',
                justifyContent: 'center', fontSize: CANCEL_BUTTON_SETTINGS.fontSize,
                zIndex: CANCEL_BUTTON_SETTINGS.zIndex, cursor: 'pointer', border: '2px solid white'
            });
            cancelButton.innerText = CANCEL_BUTTON_SETTINGS.text;
            cancelButton.setAttribute('title', 'Cancel Batch Mode');
            cancelButton.addEventListener('click', (e) => {
                e.stopPropagation();
                exitBatchMode();
            });
            document.body.appendChild(cancelButton);
            debug('Custom generate buttons created.');
        }
        clearSuggestions();
        debug('All features initialized.');
    }

    const pageObserver = new MutationObserver((mutations) => {
        if (!promptInput || !document.body.contains(promptInput)) {
            debug('MutationObserver detected promptInput missing or removed. Re-initializing all features.');
            initializeFeatures();
        }
        if (isInBatchMode && (!generateButtonObserver || !document.querySelector(ORIGINAL_GENERATE_BUTTON_SELECTOR))) {
             debug('Original button might have been re-rendered. Re-attaching observer.');
             observeGenerateButton();
        }
    });

    pageObserver.observe(document.body, { childList: true, subtree: true });

    loadTagsFromCSV().then(() => {
        initializeFeatures();
    }).catch(error => {
        console.error("Critical error during tag loading:", error);
        alert("Failed to load autocomplete tags. Please check console for details.");
    });

})();