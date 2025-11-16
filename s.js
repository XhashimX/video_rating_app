// ==UserScript==
// @name         Civitai Nested Tags Library
// @namespace    http://tampermonkey.net/nested
// @version      1.1.1
// @description  External tag library with nested sub-category support
// @author       BEM (Modified by Mentorbot, Syntax Fix by Gemini)
// @match        https://civitai.com/*
// @grant        GM.xmlHttpRequest
// @license      MIT
// ==/UserScript==

(function () {
  "use strict";

  // --- CONFIG ---
  const PROMPT_TEXTAREA_ID = "input_prompt";
  const NESTED_TAGS_URL =
    "https://gist.githubusercontent.com/gthrons5-dev/d451f7a1f3fbe586e0e2b8d27c7f34c4/raw/39863dfa2cd46b9f701a873647d6c3c5d207cce8/gistfile1.txt";
  const PROMPT_SEPARATOR = "###";

  // --- INTERNAL VARIABLES ---
  let promptInput = null;
  let nestedTagsModal = null;
  let nestedTagsData = {}; // Will hold { "category": { tags: [], subcategories: {} } }
  let selectedNestedTags = new Set();
  let nestedSuggestionsBox = null;

  // --- STYLES ---
  const styleElement = document.createElement("style");
  styleElement.textContent = `
        #nested-tags-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0, 0, 0, 0.7); display: none;
            align-items: center; justify-content: center; z-index: 100001; /* Changed Z-index to avoid overlap */
        }
        #nested-tags-modal {
            background-color: #1a1b1e; border: 1px solid #444; border-radius: 8px;
            width: 90%; max-width: 800px; max-height: 85vh;
            display: flex; flex-direction: column; box-shadow: 0 5px 20px rgba(0,0,0,0.5);
        }
        .nested-tags-header {
            padding: 10px 15px; border-bottom: 1px solid #333; display: flex;
            justify-content: space-between; align-items: center;
        }
        .nested-tags-header h3 { margin: 0; color: #E0E1E2; font-size: 18px; }
        .nested-tags-close-btn {
            background: none; border: none; color: #E0E1E2; font-size: 24px;
            cursor: pointer; padding: 0 5px;
        }
        .nested-tags-content { padding: 10px; overflow-y: auto; }
        .nested-tags-global-actions {
            background-color: #2c2f33; padding: 10px; border-radius: 5px; margin-bottom: 10px;
            display: flex; align-items: center; justify-content: space-between; gap: 10px;
            font-size: 14px; color: #E0E1E2;
        }
        .nested-tags-global-actions input[type="number"] {
            width: 60px; background-color: #1a1b1e; color: #E0E1E2; border: 1px solid #444;
            border-radius: 4px; padding: 4px; text-align: center;
        }
        .nested-tags-global-actions button {
            background-color: #5865F2; color: white; border: none; border-radius: 4px;
            padding: 5px 12px; cursor: pointer; font-weight: bold;
        }
        .nested-tags-category { margin-bottom: 10px; }
        .nested-tags-category-header {
            background-color: #282a2d; color: #98C379; padding: 8px 12px;
            border-radius: 4px; cursor: pointer; font-weight: bold;
            display: flex; align-items: center; justify-content: space-between;
        }
        .nested-tags-category-header .category-title-section {
            display: flex; align-items: center; gap: 10px; flex-grow: 1;
        }
        .nested-tags-category-header .category-title { flex-grow: 1; }
        .nested-tags-category-actions { display: flex; gap: 8px; }
        .nested-tags-category-action-btn {
            background-color: #4f545c; color: #dcddde; border: none; padding: 2px 8px;
            font-size: 12px; border-radius: 3px; cursor: pointer;
        }
        .nested-tags-tags-container {
            padding-left: 15px; max-height: 0; overflow: hidden; transition: max-height 0.3s ease;
        }
        .nested-tags-tags-container.open {
            max-height: 400px;
            overflow-y: auto;
        }
        .nested-tags-tag-item {
            display: flex; align-items: center; padding: 6px 0; color: #C1C2C5;
        }
        .nested-tags-tag-item input[type="checkbox"] { margin-right: 10px; cursor: pointer; }
        .nested-tags-tag-item .tag-name { flex-grow: 1; cursor: pointer; }
        .nested-tags-tag-item .tag-name:hover { color: #FFFFFF; }
        .nested-tags-actions {
            padding: 10px 15px; border-top: 1px solid #333; display: none;
            gap: 10px; justify-content: flex-end;
        }
        .nested-tags-action-btn {
            padding: 8px 15px; border-radius: 5px; border: none; cursor: pointer;
            font-weight: bold; color: white;
        }
        .paste-together-btn { background-color: #2a75d2; }
        .paste-separately-btn { background-color: #d22a61; }
        .nested-tags-special-button { font-weight: bold; color: #61AFEF; }
        .nested-tags-loading {
            text-align: center; padding: 20px; color: #98C379;
        }
        .nested-tags-subcategory {
            margin-left: 20px;
            border-left: 2px solid #3a3f45;
            padding-left: 10px;
            margin-top: 8px;
        }
        .nested-tags-subcategory-header {
            background-color: #303336;
            color: #A6C2FF;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: normal;
            font-size: 14px;
        }
    `;
  document.head.appendChild(styleElement);

  // --- UTILITY FUNCTIONS ---
  // [تصحيح] تم إضافة علامات الاقتباس المائلة
  function debug(msg) {
    console.log(`[Nested Tags] ${msg}`);
  }

  function setNativeValue(element, value) {
    const valueSetter = Object.getOwnPropertyDescriptor(element, "value").set;
    const prototype = Object.getPrototypeOf(element);
    const prototypeValueSetter = Object.getOwnPropertyDescriptor(
      prototype,
      "value"
    ).set;
    if (valueSetter && valueSetter !== prototypeValueSetter) {
      prototypeValueSetter.call(element, value);
    } else {
      valueSetter.call(element, value);
    }
    element.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // --- LOAD NESTED TAGS ---
  async function loadNestedTags() {
    debug("Loading nested tags from URL...");
    return new Promise((resolve, reject) => {
      GM.xmlHttpRequest({
        method: "GET",
        url: NESTED_TAGS_URL,
        onload: function (response) {
          if (response.status === 200) {
            try {
              parseNestedTagsFile(response.responseText);
              // [تصحيح] تم إضافة علامات الاقتباس المائلة
              debug(
                `Successfully loaded ${
                  Object.keys(nestedTagsData).length
                } categories.`
              );
              resolve();
            } catch (e) {
              console.error("Error parsing nested tags:", e);
              reject(e);
            }
          } else {
            console.error(
              "Failed to load nested tags:",
              response.status,
              response.statusText
            );
            // [تصحيح] تم إضافة علامات الاقتباس المائلة
            reject(new Error(`Failed to load: ${response.status}`));
          }
        },
        onerror: function (error) {
          console.error("Nested tags request error:", error);
          reject(error);
        },
      });
    });
  }

  function parseNestedTagsFile(fileContent) {
    const lines = fileContent.split("\n");
    let currentCategory = null;
    let currentSubCategory = null;

    nestedTagsData = {};

    for (let line of lines) {
      line = line.trim();
      if (!line) continue;

      if (line.startsWith("#")) {
        currentCategory = line.substring(1).trim();
        currentCategory = currentCategory
          .replace(/\.txt$/i, "")
          .replace(/^dan_/i, "")
          .replace(/_/g, " ");
        currentCategory = currentCategory
          .split(" ")
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(" ");

        if (!nestedTagsData[currentCategory]) {
          nestedTagsData[currentCategory] = {
            tags: [],
            subcategories: {},
          };
        }
        currentSubCategory = null;
        // [تصحيح] تم إضافة علامات الاقتباس المائلة
        debug(`Found category: ${currentCategory}`);
      } else if (line.startsWith("~") && currentCategory) {
        currentSubCategory = line.substring(1).trim();
        if (
          !nestedTagsData[currentCategory].subcategories[currentSubCategory]
        ) {
          nestedTagsData[currentCategory].subcategories[currentSubCategory] =
            [];
        }
        // [تصحيح] تم إضافة علامات الاقتباس المائلة
        debug(
          `Found sub-category: ${currentSubCategory} under ${currentCategory}`
        );
      } else if (
        line.startsWith("-") &&
        currentCategory &&
        currentSubCategory
      ) {
        const tag = line.substring(1).trim();
        if (tag) {
          nestedTagsData[currentCategory].subcategories[
            currentSubCategory
          ].push(tag);
        }
        currentSubCategory = null;
      } else if (currentCategory) {
        if (currentSubCategory) {
          nestedTagsData[currentCategory].subcategories[
            currentSubCategory
          ].push(line);
        } else {
          nestedTagsData[currentCategory].tags.push(line);
        }
      }
    }

    let totalTags = 0;
    Object.values(nestedTagsData).forEach((catData) => {
      totalTags += catData.tags.length;
      Object.values(catData.subcategories).forEach((subCatTags) => {
        totalTags += subCatTags.length;
      });
    });
    // [تصحيح] تم إضافة علامات الاقتباس المائلة
    debug(
      `Parsed ${
        Object.keys(nestedTagsData).length
      } categories with ${totalTags} total tags.`
    );
  }

  // --- MODAL FUNCTIONS ---
  function createNestedTagsModal() {
    if (nestedTagsModal && document.body.contains(nestedTagsModal)) return;

    const overlay = document.createElement("div");
    overlay.id = "nested-tags-overlay";

    const modal = document.createElement("div");
    modal.id = "nested-tags-modal";

    const header = document.createElement("div");
    header.className = "nested-tags-header";
    const title = document.createElement("h3");
    title.textContent = "Nested Tags Library";
    const closeBtn = document.createElement("button");
    closeBtn.className = "nested-tags-close-btn";
    closeBtn.innerHTML = "&times;";
    closeBtn.onclick = closeNestedTagsModal;
    header.appendChild(title);
    header.appendChild(closeBtn);

    const content = document.createElement("div");
    content.className = "nested-tags-content";

    const globalActions = document.createElement("div");
    globalActions.className = "nested-tags-global-actions";
    globalActions.innerHTML = `
            <span>Random Selection from Selected Categories:</span>
            <input type="number" id="nested-global-random-count" value="2" min="1">
            <button id="nested-global-random-btn">Select</button>
        `;

    const actions = document.createElement("div");
    actions.className = "nested-tags-actions";
    const pasteTogetherBtn = document.createElement("button");
    pasteTogetherBtn.className = "nested-tags-action-btn paste-together-btn";
    pasteTogetherBtn.textContent = "Paste Together";
    pasteTogetherBtn.onclick = handleNestedPasteTogether;
    const pasteSeparatelyBtn = document.createElement("button");
    pasteSeparatelyBtn.className =
      "nested-tags-action-btn paste-separately-btn";
    pasteSeparatelyBtn.textContent = "Paste Separately";
    pasteSeparatelyBtn.onclick = handleNestedPasteSeparately;
    actions.appendChild(pasteTogetherBtn);
    actions.appendChild(pasteSeparatelyBtn);

    modal.appendChild(header);
    content.appendChild(globalActions);
    modal.appendChild(content);
    modal.appendChild(actions);
    overlay.appendChild(modal);

    nestedTagsModal = overlay;
    document.body.appendChild(nestedTagsModal);

    nestedTagsModal
      .querySelector("#nested-global-random-btn")
      .addEventListener("click", handleNestedGlobalRandomSelect);

    renderNestedTagsContent();
  }

  function createTagItem(tag) {
    const item = document.createElement("div");
    item.className = "nested-tags-tag-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.tag = tag;
    checkbox.onchange = () =>
      handleNestedTagCheckboxChange(tag, checkbox.checked);

    const name = document.createElement("span");
    name.className = "tag-name";
    name.textContent = tag.replace(/_/g, " ");
    name.onclick = () => handleNestedTagNameClick(tag);

    item.appendChild(checkbox);
    item.appendChild(name);
    return item;
  }

  function renderNestedTagsContent() {
    const contentArea = nestedTagsModal.querySelector(".nested-tags-content");
    contentArea
      .querySelectorAll(".nested-tags-category")
      .forEach((el) => el.remove());

    if (Object.keys(nestedTagsData).length === 0) {
      const loadingDiv = document.createElement("div");
      loadingDiv.className = "nested-tags-loading";
      loadingDiv.textContent = "Loading tags...";
      contentArea.appendChild(loadingDiv);
      return;
    }

    for (const category in nestedTagsData) {
      const categoryData = nestedTagsData[category];
      const categoryDiv = document.createElement("div");
      categoryDiv.className = "nested-tags-category";

      const header = document.createElement("div");
      header.className = "nested-tags-category-header";

      const titleSection = document.createElement("div");
      titleSection.className = "category-title-section";

      const categoryCheckbox = document.createElement("input");
      categoryCheckbox.type = "checkbox";
      categoryCheckbox.title =
        "Select this category for global random selection";
      categoryCheckbox.dataset.category = category;

      const title = document.createElement("span");
      title.className = "category-title";
      title.textContent = category;

      titleSection.appendChild(categoryCheckbox);
      titleSection.appendChild(title);
      titleSection.onclick = (e) => {
        if (e.target.type !== "checkbox") {
          categoryDiv
            .querySelectorAll(".nested-tags-tags-container")
            .forEach((container) => {
              container.classList.toggle("open");
            });
        }
      };

      const categoryActions = document.createElement("div");
      categoryActions.className = "nested-tags-category-actions";

      const selectAllBtn = document.createElement("button");
      selectAllBtn.className = "nested-tags-category-action-btn";
      selectAllBtn.textContent = "Select All";
      selectAllBtn.onclick = (e) => {
        e.stopPropagation();
        handleNestedSelectAllInCategory(category, categoryDiv, selectAllBtn);
      };

      const randomBtn = document.createElement("button");
      randomBtn.className = "nested-tags-category-action-btn";
      randomBtn.textContent = "Random (+2)";
      randomBtn.onclick = (e) => {
        e.stopPropagation();
        handleNestedRandomSelectInCategory(category, categoryDiv);
      };

      categoryActions.appendChild(selectAllBtn);
      categoryActions.appendChild(randomBtn);
      header.appendChild(titleSection);
      header.appendChild(categoryActions);
      categoryDiv.appendChild(header);

      if (categoryData.tags.length > 0) {
        const mainTagsContainer = document.createElement("div");
        mainTagsContainer.className = "nested-tags-tags-container";
        categoryData.tags.forEach((tag) => {
          mainTagsContainer.appendChild(createTagItem(tag));
        });
        categoryDiv.appendChild(mainTagsContainer);
      }

      for (const subCategoryName in categoryData.subcategories) {
        const subCategoryTags = categoryData.subcategories[subCategoryName];
        const subCategoryDiv = document.createElement("div");
        subCategoryDiv.className = "nested-tags-subcategory";

        const subHeader = document.createElement("div");
        subHeader.className = "nested-tags-subcategory-header";
        subHeader.textContent = subCategoryName;

        const subTagsContainer = document.createElement("div");
        subTagsContainer.className = "nested-tags-tags-container";

        subHeader.onclick = () => {
          subTagsContainer.classList.toggle("open");
        };

        subCategoryTags.forEach((tag) => {
          subTagsContainer.appendChild(createTagItem(tag));
        });

        subCategoryDiv.appendChild(subHeader);
        subCategoryDiv.appendChild(subTagsContainer);
        categoryDiv.appendChild(subCategoryDiv);
      }

      contentArea.appendChild(categoryDiv);
    }
  }

  function openNestedTagsModal() {
    if (!nestedTagsModal) createNestedTagsModal();
    selectedNestedTags.clear();
    nestedTagsModal
      .querySelectorAll('input[type="checkbox"]')
      .forEach((cb) => (cb.checked = false));
    nestedTagsModal
      .querySelectorAll(".nested-tags-category-action-btn")
      .forEach((btn) => {
        if (btn.textContent.includes("Deselect"))
          btn.textContent = "Select All";
      });
    updateNestedTagsActions();
    nestedTagsModal.style.display = "flex";
  }

  function closeNestedTagsModal() {
    if (nestedTagsModal) nestedTagsModal.style.display = "none";
  }

  function handleNestedTagCheckboxChange(tag, isChecked) {
    if (isChecked) {
      selectedNestedTags.add(tag);
    } else {
      selectedNestedTags.delete(tag);
    }
    updateNestedTagsActions();
  }

  function handleNestedTagNameClick(tag) {
    insertTag(tag);
    closeNestedTagsModal();
  }

  function updateNestedTagsActions() {
    const actionsDiv = nestedTagsModal.querySelector(".nested-tags-actions");
    actionsDiv.style.display = selectedNestedTags.size > 0 ? "flex" : "none";
  }

  function handleNestedPasteTogether() {
    if (selectedNestedTags.size === 0 || !promptInput) return;
    const tagsToInsert = Array.from(selectedNestedTags).join(", ");
    const currentPrompt = promptInput.value.trim();
    const separator = currentPrompt && !currentPrompt.endsWith(",") ? ", " : "";
    const newPrompt = currentPrompt + separator + tagsToInsert;
    setNativeValue(promptInput, newPrompt);
    closeNestedTagsModal();
    promptInput.focus();
  }

  function handleNestedPasteSeparately() {
    if (selectedNestedTags.size === 0 || !promptInput) return;
    const basePrompt = promptInput.value.trim();
    const newPrompts = Array.from(selectedNestedTags).map((tag) => {
      return tag + (basePrompt ? ", " + basePrompt : "");
    });
    // [تصحيح] تم إضافة علامات الاقتباس المائلة
    const finalPromptText = newPrompts.join(`\n${PROMPT_SEPARATOR}\n`);
    setNativeValue(promptInput, finalPromptText);
    closeNestedTagsModal();
  }

  function handleNestedSelectAllInCategory(categoryName, categoryDiv, button) {
    const checkboxes = categoryDiv.querySelectorAll(
      'input[type="checkbox"][data-tag]'
    );
    const isSelectAllAction = button.textContent === "Select All";

    checkboxes.forEach((cb) => {
      const tag = cb.dataset.tag;
      if (cb.checked !== isSelectAllAction) {
        cb.checked = isSelectAllAction;
        handleNestedTagCheckboxChange(tag, isSelectAllAction);
      }
    });

    button.textContent = isSelectAllAction ? "Deselect All" : "Select All";
  }

  function handleNestedRandomSelectInCategory(categoryName, categoryDiv) {
    const categoryData = nestedTagsData[categoryName];
    let allTagsInCategory = [...categoryData.tags];
    Object.values(categoryData.subcategories).forEach((subCatTags) => {
      allTagsInCategory.push(...subCatTags);
    });

    const availableTags = allTagsInCategory.filter(
      (tag) => !selectedNestedTags.has(tag)
    );

    if (availableTags.length === 0) {
      // [تصحيح] تم إضافة علامات الاقتباس المائلة
      debug(`No unselected tags left in ${categoryName}`);
      return;
    }

    const shuffled = availableTags.sort(() => 0.5 - Math.random());
    const tagsToSelect = shuffled.slice(0, 2);

    tagsToSelect.forEach((tag) => {
      // [تصحيح] تم إضافة علامات الاقتباس المائلة
      const checkbox = categoryDiv.querySelector(
        `input[data-tag="${CSS.escape(tag)}"]`
      );
      if (checkbox && !checkbox.checked) {
        checkbox.checked = true;
        handleNestedTagCheckboxChange(tag, true);
      }
    });
  }

  function handleNestedGlobalRandomSelect() {
    const countInput = nestedTagsModal.querySelector(
      "#nested-global-random-count"
    );
    const numToSelect = parseInt(countInput.value, 10);
    if (isNaN(numToSelect) || numToSelect <= 0) return;

    const selectedCategories = Array.from(
      nestedTagsModal.querySelectorAll(
        '.nested-tags-category-header .category-title-section input[type="checkbox"]:checked'
      )
    ).map((cb) => cb.dataset.category);

    if (selectedCategories.length === 0) {
      alert(
        "Please select at least one category first (using the checkbox next to the category name)."
      );
      return;
    }

    let tagPool = [];
    selectedCategories.forEach((catName) => {
      const categoryData = nestedTagsData[catName];
      if (categoryData) {
        tagPool.push(...categoryData.tags);
        Object.values(categoryData.subcategories).forEach((subCatTags) => {
          tagPool.push(...subCatTags);
        });
      }
    });

    const availableTags = tagPool.filter((tag) => !selectedNestedTags.has(tag));
    const uniqueAvailableTags = [...new Set(availableTags)];

    const shuffled = uniqueAvailableTags.sort(() => 0.5 - Math.random());
    const tagsToSelect = shuffled.slice(0, numToSelect);

    tagsToSelect.forEach((tag) => {
      // [تصحيح] تم إضافة علامات الاقتباس المائلة
      const checkbox = nestedTagsModal.querySelector(
        `input[data-tag="${CSS.escape(tag)}"]`
      );
      if (checkbox && !checkbox.checked) {
        checkbox.checked = true;
        handleNestedTagCheckboxChange(tag, true);
      }
    });
  }

  function insertTag(tag) {
    if (!promptInput) return;
    const currentText = promptInput.value;
    const cursorPosition = promptInput.selectionStart;

    const textBeforeCursor = currentText.substring(0, cursorPosition);
    const lastCommaIndex = textBeforeCursor.lastIndexOf(",");

    let startPos;
    if (lastCommaIndex !== -1) {
      startPos = lastCommaIndex + 1;
      const word = textBeforeCursor.substring(startPos).trim();
      if (word) {
        const leadingSpaces =
          textBeforeCursor.substring(startPos).length -
          textBeforeCursor.substring(startPos).trimLeft().length;
        startPos = startPos + leadingSpaces;
      }
    } else {
      startPos = 0;
    }

    const textBeforeWord = currentText.substring(0, startPos);
    const textAfterWord = currentText.substring(cursorPosition);
    let newText = textBeforeWord + tag + ", " + textAfterWord;

    if (currentText.trim() === "") newText = tag + ", ";

    const newCursorPosition = textBeforeWord.length + tag.length + 2;
    setNativeValue(promptInput, newText);
    promptInput.setSelectionRange(newCursorPosition, newCursorPosition);
    promptInput.focus();
  }

  // --- INJECT BUTTON INTO AUTOCOMPLETE ---
  function injectNestedTagsButton() {
    const checkInterval = setInterval(() => {
      nestedSuggestionsBox = document.getElementById(
        "simple-autocomplete-suggestions-box"
      );
      if (nestedSuggestionsBox) {
        clearInterval(checkInterval);
        debug(
          "Found autocomplete suggestions box. Will inject button on next show."
        );
        observeNestedSuggestionsBox();
      }
    }, 1000);
  }

  function observeNestedSuggestionsBox() {
    const observer = new MutationObserver(() => {
      if (nestedSuggestionsBox.style.display === "block") {
        injectNestedButtonIfNeeded();
      }
    });

    observer.observe(nestedSuggestionsBox, {
      attributes: true,
      attributeFilter: ["style"],
    });
  }

  function injectNestedButtonIfNeeded() {
    if (nestedSuggestionsBox.querySelector(".nested-tags-special-button"))
      return;
    const mySuggestionsButton = nestedSuggestionsBox.querySelector(
      ".my-suggestions-special-button"
    );
    if (!mySuggestionsButton) return;

    const nestedTagsButton = document.createElement("div");
    // [تصحيح] تم إضافة علامات الاقتباس
    nestedTagsButton.innerHTML = "Nested Tags 📂";
    nestedTagsButton.className = "nested-tags-special-button";
    nestedTagsButton.addEventListener("click", openNestedTagsModal);

    mySuggestionsButton.parentNode.insertBefore(
      nestedTagsButton,
      mySuggestionsButton.nextSibling
    );
    debug("Nested Tags button injected into autocomplete.");
  }

  // --- INITIALIZATION ---
  function initialize() {
    promptInput = document.getElementById(PROMPT_TEXTAREA_ID);
    if (!promptInput) {
      debug("Prompt textarea not found yet. Retrying...");
      setTimeout(initialize, 1000);
      return;
    }

    debug("Initializing Nested Tags feature...");

    loadNestedTags()
      .then(() => {
        createNestedTagsModal();
        injectNestedTagsButton();
        debug("Nested Tags feature initialized.");
      })
      .catch((error) => {
        console.error("Failed to load nested tags:", error);
        alert("Failed to load nested tags library. Check console for details.");
      });
  }

  // Start initialization
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
