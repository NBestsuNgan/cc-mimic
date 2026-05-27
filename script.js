// ===== SAMPLE TWEET DATA =====
const tweets = [
  {
    id: 1,
    name: "Elon Musk",
    handle: "@elonmusk",
    verified: true,
    time: "2h",
    text: "The future of AI is going to be incredible. We're living in the most exciting time in human history. 🚀",
    avatar: "E",
    avatarColor: "#1d9bf0",
    replies: "12.4K",
    reposts: "45.2K",
    likes: "289K",
    views: "12.5M",
    liked: false,
    reposted: false,
    bookmarked: false,
  },
  {
    id: 2,
    name: "NASA",
    handle: "@NASA",
    verified: true,
    time: "4h",
    text: "Our Perseverance rover has captured stunning new images of Mars' surface. The geological formations tell a story spanning billions of years.\n\n🔴 #Mars #SpaceExploration",
    avatar: "N",
    avatarColor: "#f91880",
    replies: "3.2K",
    reposts: "18.7K",
    likes: "98.3K",
    views: "4.2M",
    liked: false,
    reposted: false,
    bookmarked: false,
    media: "https://picsum.photos/seed/mars/560/300",
  },
  {
    id: 3,
    name: "The Verge",
    handle: "@verge",
    verified: true,
    time: "5h",
    text: "Apple announces new M4 chip lineup at their spring event. The performance improvements are staggering — up to 50% faster than M3 in multi-threaded workloads. #AppleEvent",
    avatar: "T",
    avatarColor: "#00ba7c",
    replies: "2.1K",
    reposts: "8.9K",
    likes: "34.5K",
    views: "1.8M",
    liked: false,
    reposted: false,
    bookmarked: false,
  },
  {
    id: 4,
    name: "BBC News",
    handle: "@BBCNews",
    verified: true,
    time: "7h",
    text: "Breaking: Global temperatures in 2024 have exceeded 1.5°C above pre-industrial levels for the first time on record, according to new climate data.",
    avatar: "B",
    avatarColor: "#ff0000",
    replies: "8.7K",
    reposts: "52.1K",
    likes: "142K",
    views: "8.9M",
    liked: false,
    reposted: false,
    bookmarked: false,
  },
  {
    id: 5,
    name: "Product Hunt",
    handle: "@ProductHunt",
    verified: true,
    time: "9h",
    text: "🌟 Product of the Day: A new tool that uses AI to generate production-ready code from natural language descriptions.\n\nShip faster, iterate quicker. Who's tried this?",
    avatar: "P",
    avatarColor: "#da552f",
    replies: "891",
    reposts: "3.4K",
    likes: "12.7K",
    views: "956K",
    liked: false,
    reposted: false,
    bookmarked: false,
  },
  {
    id: 6,
    name: "TechCrunch",
    handle: "@TechCrunch",
    verified: true,
    time: "11h",
    text: "OpenAI's latest model demonstrates remarkable reasoning capabilities, solving complex math problems and writing sophisticated code. GPT-5 is coming soon.",
    avatar: "T",
    avatarColor: "#0d9443",
    replies: "4.5K",
    reposts: "21.3K",
    likes: "87.2K",
    views: "5.1M",
    liked: false,
    reposted: false,
    bookmarked: false,
  },
];

// ===== SVG ICONS =====
const SVG = {
  reply: `<svg viewBox="0 0 24 24"><path d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.96-1.607 5.68-4.196 7.11l-8.054 4.46v-3.69h-.067c-4.49.1-8.183-3.51-8.183-8.01zm8.005-6c-3.317 0-6.005 2.69-6.005 6 0 3.37 2.77 6.08 6.138 6.01l.351-.01h1.761v2.3l5.087-2.81c1.951-1.08 3.163-3.13 3.163-5.36 0-3.39-2.744-6.13-6.129-6.13H9.756z"/></svg>`,
  repost: `<svg viewBox="0 0 24 24"><path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"/></svg>`,
  like: `<svg viewBox="0 0 24 24"><path d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.561-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"/></svg>`,
  likeFilled: `<svg viewBox="0 0 24 24"><path d="M20.884 13.19c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"/></svg>`,
  views: `<svg viewBox="0 0 24 24"><path d="M8.75 21V3h2v18h-2zM18 21V8.5h2V21h-2zM4 21l.004-10h2L6 21H4zm9.248 0v-7h2v7h-2z"/></svg>`,
  bookmark: `<svg viewBox="0 0 24 24"><path d="M4 4.5C4 3.12 5.119 2 6.5 2h11C18.881 2 20 3.12 20 4.5v18.44l-8-5.71-8 5.71V4.5zM6.5 4c-.276 0-.5.22-.5.5v14.56l6-4.29 6 4.29V4.5c0-.28-.224-.5-.5-.5h-11z"/></svg>`,
  bookmarkFilled: `<svg viewBox="0 0 24 24"><path d="M4 4.5C4 3.12 5.119 2 6.5 2h11C18.881 2 20 3.12 20 4.5v18.44l-8-5.71-8 5.71V4.5z"/></svg>`,
  share: `<svg viewBox="0 0 24 24"><path d="M12 2.59l5.7 5.7-1.41 1.42L13 6.41V16h-2V6.41l-3.3 3.3-1.41-1.42L12 2.59zM21 15l-.02 3.51c0 1.38-1.12 2.49-2.5 2.49H5.5C4.11 21 3 19.88 3 18.5V15h2v3.5c0 .28.22.5.5.5h12.98c.28 0 .5-.22.5-.5L19 15h2z"/></svg>`,
};

// ===== STATE =====
let currentFeed = "for-you";
let currentTab = "home";

// ===== DOM ELEMENTS =====
const feedEl = document.getElementById("feed");
const composeInput = document.getElementById("composeInput");
const postBtn = document.getElementById("postBtn");
const charCount = document.getElementById("charCount");
const tabs = document.querySelectorAll(".tab");
const navItems = document.querySelectorAll(".nav-item");
const pageTitle = document.querySelector(".page-title");
const followBtns = document.querySelectorAll(".follow-btn");

// ===== RENDER TWEETS =====
function formatCount(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
  if (num >= 1000) return (num / 1000).toFixed(1).replace(/\.0$/, "") + "K";
  return num.toString();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function linkifyText(text) {
  let html = escapeHtml(text);
  html = html.replace(/#(\w+)/g, '<span class="hashtag">#$1</span>');
  html = html.replace(/@(\w+)/g, '<span class="mention">@$1</span>');
  html = html.replace(/\n/g, "<br>");
  return html;
}

function renderTweet(tweet) {
  const likeSvg = tweet.liked ? SVG.likeFilled : SVG.like;
  const bookmarkSvg = tweet.bookmarked ? SVG.bookmarkFilled : SVG.bookmark;

  return `
    <div class="tweet" data-id="${tweet.id}">
      <div class="tweet-avatar" style="background:${tweet.avatarColor}">${tweet.avatar}</div>
      <div class="tweet-body">
        <div class="tweet-header">
          <span class="tweet-name">${escapeHtml(tweet.name)}</span>
          ${tweet.verified ? '<svg class="verified" viewBox="0 0 22 22"><path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.69-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.636.433 1.221.878 1.69.47.446 1.055.752 1.69.883.635.13 1.294.083 1.902-.143.271.586.702 1.084 1.24 1.438.54.354 1.167.551 1.813.568.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.225 1.261.272 1.893.143.636-.131 1.22-.437 1.69-.883.445-.47.75-1.055.88-1.69.131-.633.084-1.29-.139-1.896.586-.274 1.084-.705 1.438-1.246.356-.54.553-1.17.57-1.817zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"/></svg>' : ""}
          <span class="tweet-handle">${escapeHtml(tweet.handle)}</span>
          <span class="tweet-dot">·</span>
          <span class="tweet-time">${tweet.time}</span>
          <button class="tweet-more">
            <svg viewBox="0 0 24 24"><path d="M3 12c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm9 2c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm7 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/></svg>
          </button>
        </div>
        <div class="tweet-text">${linkifyText(tweet.text)}</div>
        ${tweet.media ? `<div class="tweet-media"><img src="${tweet.media}" alt="Tweet media" loading="lazy" /></div>` : ""}
        <div class="tweet-actions">
          <button class="tweet-action reply" data-action="reply" data-id="${tweet.id}">
            ${SVG.reply}
            <span class="tweet-action-count">${tweet.replies}</span>
          </button>
          <button class="tweet-action repost ${tweet.reposted ? "active" : ""}" data-action="repost" data-id="${tweet.id}">
            ${SVG.repost}
            <span class="tweet-action-count">${tweet.reposts}</span>
          </button>
          <button class="tweet-action like ${tweet.liked ? "active" : ""}" data-action="like" data-id="${tweet.id}">
            ${likeSvg}
            <span class="tweet-action-count">${tweet.likes}</span>
          </button>
          <button class="tweet-action views" data-action="views" data-id="${tweet.id}">
            ${SVG.views}
            <span class="tweet-action-count">${tweet.views}</span>
          </button>
          <div style="display:flex;gap:0;">
            <button class="tweet-action bookmark ${tweet.bookmarked ? "active" : ""}" data-action="bookmark" data-id="${tweet.id}">
              ${bookmarkSvg}
            </button>
            <button class="tweet-action share" data-action="share" data-id="${tweet.id}">
              ${SVG.share}
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderFeed() {
  feedEl.innerHTML = tweets.map(renderTweet).join("");
}

// ===== COMPOSE TWEET =====
composeInput.addEventListener("input", function () {
  const len = this.value.length;
  const remaining = 280 - len;

  if (len > 0) {
    charCount.textContent = remaining;
    postBtn.disabled = false;
  } else {
    charCount.textContent = "";
    postBtn.disabled = true;
  }

  charCount.classList.remove("warning", "danger");
  if (remaining <= 0) {
    charCount.classList.add("danger");
  } else if (remaining <= 20) {
    charCount.classList.add("warning");
  }

  // Auto-resize
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 200) + "px";
});

postBtn.addEventListener("click", function () {
  const text = composeInput.value.trim();
  if (!text) return;

  const newTweet = {
    id: Date.now(),
    name: "John Doe",
    handle: "@johndoe",
    verified: false,
    time: "now",
    text: text,
    avatar: "𝕏",
    avatarColor: "#1d9bf0",
    replies: "0",
    reposts: "0",
    likes: "0",
    views: "0",
    liked: false,
    reposted: false,
    bookmarked: false,
  };

  tweets.unshift(newTweet);
  renderFeed();

  composeInput.value = "";
  composeInput.style.height = "auto";
  charCount.textContent = "";
  postBtn.disabled = true;
});

// ===== TWEET ACTIONS (Event Delegation) =====
feedEl.addEventListener("click", function (e) {
  const actionBtn = e.target.closest(".tweet-action");
  if (!actionBtn) return;

  const action = actionBtn.dataset.action;
  const id = parseInt(actionBtn.dataset.id);
  const tweet = tweets.find((t) => t.id === id);
  if (!tweet) return;

  const countEl = actionBtn.querySelector(".tweet-action-count");

  switch (action) {
    case "like":
      tweet.liked = !tweet.liked;
      actionBtn.classList.toggle("active", tweet.liked);
      actionBtn.querySelector("svg").outerHTML = tweet.liked ? SVG.likeFilled : SVG.like;
      if (countEl) {
        const currentLikes = parseInt(tweet.likes.replace("K", "000").replace("M", "000000"));
        const newCount = tweet.liked ? currentLikes + 1 : currentLikes - 1;
        tweet.likes = formatCount(newCount);
        countEl.textContent = tweet.likes;
      }
      // Heart animation
      if (tweet.liked) {
        actionBtn.style.transform = "scale(1.2)";
        setTimeout(() => (actionBtn.style.transform = "scale(1)"), 150);
      }
      break;

    case "repost":
      tweet.reposted = !tweet.reposted;
      actionBtn.classList.toggle("active", tweet.reposted);
      if (countEl) {
        const currentReposts = parseInt(tweet.reposts.replace("K", "000").replace("M", "000000"));
        const newCount = tweet.reposted ? currentReposts + 1 : currentReposts - 1;
        tweet.reposts = formatCount(newCount);
        countEl.textContent = tweet.reposts;
      }
      break;

    case "bookmark":
      tweet.bookmarked = !tweet.bookmarked;
      actionBtn.classList.toggle("active", tweet.bookmarked);
      actionBtn.querySelector("svg").outerHTML = tweet.bookmarked ? SVG.bookmarkFilled : SVG.bookmark;
      break;

    case "reply":
      // Visual feedback only
      actionBtn.style.transform = "scale(1.1)";
      setTimeout(() => (actionBtn.style.transform = "scale(1)"), 150);
      break;

    case "share":
      // Visual feedback only
      actionBtn.style.transform = "scale(1.1)";
      setTimeout(() => (actionBtn.style.transform = "scale(1)"), 150);
      break;
  }
});

// ===== TAB SWITCHING =====
tabs.forEach((tab) => {
  tab.addEventListener("click", function () {
    tabs.forEach((t) => t.classList.remove("active"));
    this.classList.add("active");
    currentFeed = this.dataset.feed;

    // Animate feed transition
    feedEl.style.opacity = "0.5";
    setTimeout(() => {
      feedEl.style.opacity = "1";
    }, 200);
  });
});

// ===== NAV SWITCHING =====
navItems.forEach((item) => {
  item.addEventListener("click", function () {
    navItems.forEach((i) => i.classList.remove("active"));
    this.classList.add("active");
    currentTab = this.dataset.tab;

    const label = this.querySelector(".nav-label")?.textContent || "Home";
    pageTitle.textContent = label;

    // Animate feed
    feedEl.style.opacity = "0.3";
    feedEl.style.transform = "translateY(10px)";
    setTimeout(() => {
      feedEl.style.opacity = "1";
      feedEl.style.transform = "translateY(0)";
    }, 200);
  });
});

// ===== FOLLOW BUTTONS =====
document.querySelectorAll(".follow-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    const isFollowing = this.classList.contains("following");
    if (isFollowing) {
      this.classList.remove("following");
      this.textContent = "Follow";
    } else {
      this.classList.add("following");
      this.textContent = "Following";
    }
  });
});

// ===== TREND ITEMS =====
document.querySelectorAll(".trend-item").forEach((item) => {
  item.addEventListener("click", function () {
    const trendName = this.querySelector(".trend-name")?.textContent;
    if (trendName) {
      pageTitle.textContent = trendName;
      navItems.forEach((i) => i.classList.remove("active"));
      const exploreItem = document.querySelector('[data-tab="explore"]');
      if (exploreItem) exploreItem.classList.add("active");
    }
  });
});

// ===== SMOOTH TRANSITIONS =====
feedEl.style.transition = "opacity 0.2s ease, transform 0.2s ease";

// ===== KEYBOARD SHORTCUT =====
document.addEventListener("keydown", function (e) {
  // Ctrl+Enter to post
  if (e.ctrlKey && e.key === "Enter" && composeInput.value.trim()) {
    postBtn.click();
  }
  // 'n' to focus compose (when not already focused)
  if (e.key === "n" && document.activeElement !== composeInput) {
    e.preventDefault();
    composeInput.focus();
  }
});

// ===== INIT =====
renderFeed();
