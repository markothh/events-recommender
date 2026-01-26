let searchQuery = null;
const PAGE_SIZE = 32;

let currentPage = 1;
let lastLat = null;
let lastLon = null;

// глобальные jQuery-селекторы
const $recs = $("#recs");
const $pagination = $("#pagination");

$(function () {
    // кнопка обновления рекомендаций
    $("#btn-refresh-recs").click(() => {
        searchQuery = null;
        getLocationAndLoadRecs();
    });

    // кнопка поиска
    $("#btn-search").click(() => {
        const value = $("#search").val().trim();
        if (!value) {
            searchQuery = null;
            getLocationAndLoadRecs();
            return;
        }
        searchQuery = value;
        loadSearch(1);
    });

    // Enter в поле поиска
    $("#search").on("keypress", function(e) {
        if (e.which === 13) {
            const value = $(this).val().trim();
            if (!value) {
                searchQuery = null;
                getLocationAndLoadRecs();
                return;
            }
            searchQuery = value;
            loadSearch(1);
        }
    });

    getLocationAndLoadRecs();
});

/* ---------- Рекомендации ---------- */

function getLocationAndLoadRecs() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            pos => loadRecommendations(1, pos.coords.latitude, pos.coords.longitude),
            err => loadRecommendations(1, null, null)
        );
    } else {
        loadRecommendations(1, null, null);
    }
}

function loadRecommendations(page, lat, lon) {
    lastLat = lat;
    lastLon = lon;
    currentPage = page;

    $.ajax({
        url: "/api/recommendations",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            lat: lat,
            lon: lon,
            page: page,
            page_size: PAGE_SIZE
        }),
        success: function (data) {
            renderResults(data, "Нет рекомендаций по текущим интересам.");
        },
        error: function () {
            $recs.html(`
                <div class="alert alert-danger">
                    Не удалось загрузить рекомендации
                </div>
            `);
        }
    });
}

/* ---------- Поиск ---------- */

function loadSearch(page) {
    currentPage = page;

    $.ajax({
        url: "/api/search",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            query: searchQuery,
            page: page,
            page_size: PAGE_SIZE
        }),
        success: function (data) {
            renderResults(data, "Ничего не найдено");
        },
        error: function () {
            $recs.html(`
                <div class="alert alert-danger">
                    Ошибка поиска
                </div>
            `);
        }
    });
}

/* ---------- Универсальная функция рендера ---------- */

function renderResults(data, emptyMessage) {
    $recs.empty();
    $pagination.empty();

    if (!data.items || data.items.length === 0) {
        $recs.append(`
            <div class="alert alert-warning">${emptyMessage}</div>
        `);
        return;
    }

    renderCards(data.items);
    renderPagination(data.page, data.page_size, data.total);
}

function renderCards(events) {
    let row;

    events.forEach((event, idx) => {
        if (idx % 4 === 0) {
            row = $('<div class="row g-3 mb-3"></div>');
            $recs.append(row);
        }

        const matchedTags = (event.matched_tags || [])
            .map(t => `<span class="badge bg-secondary me-1">${t}</span>`)
            .join(" ");

        const card = $(`
            <div class="col-md-3">
                <div class="event-card"
                     style="
                        cursor: pointer;
                        width: 100%;
                        height: 260px;
                        background: ${event.thumbnail
                            ? `url(${event.thumbnail}) center/cover no-repeat`
                            : '#f0f0f0'};
                        color: white;
                        border-radius: 8px;
                        position: relative;
                        overflow: hidden;
                        display: block;
                     ">

                    <div class="event-title"
                         style="
                            position: absolute;
                            top: 0;
                            left: 0;
                            width: 100%;
                            background: rgba(0,0,0,0.55);
                            padding: 6px 10px;
                            font-weight: 600;
                            font-size: 0.95rem;
                            text-shadow: 0 1px 2px black;
                         ">
                        ${event.title}
                    </div>

                    <div class="event-bottom"
                         style="
                            position: absolute;
                            bottom: 0;
                            left: 0;
                            width: 100%;
                            background: rgba(0,0,0,0.55);
                            padding: 6px 10px;
                            font-size: 0.85rem;
                         ">

                        ${event.place ? `
                            <div class="event-place"
                                 style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                <i class="bi bi-geo-alt"></i> ${event.place}
                            </div>
                        ` : ''}

                        <div class="matched-tags"
                             style="
                                margin-top: 6px;
                                display: none;
                                font-size: 0.9rem;
                             ">
                            ${matchedTags}
                        </div>
                    </div>
                </div>
            </div>
        `);

        card.find(".event-card").hover(
            function () { $(this).find(".matched-tags").slideDown(100); },
            function () { $(this).find(".matched-tags").slideUp(100); }
        );

        card.find(".event-card").click(() => {
            window.location.href = `/event/${event.id}`;
        });

        row.append(card);
    });
}

/* ---------- Пагинация ---------- */

function renderPagination(page, pageSize, total) {
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return;

    const windowSize = 2;
    const start = Math.max(2, page - windowSize);
    const end = Math.min(totalPages - 1, page + windowSize);

    function addPage(p) {
        const li = $(`
            <li class="page-item ${p === page ? "active" : ""}">
                <a class="page-link" href="#">${p}</a>
            </li>
        `);

        li.click(function (e) {
            e.preventDefault();

            if (searchQuery) {
                loadSearch(p);
            } else {
                loadRecommendations(p, lastLat, lastLon);
            }

            window.scrollTo({ top: 0, behavior: "smooth" });
        });

        $pagination.append(li);
    }

    function addDots() {
        $pagination.append(`
            <li class="page-item disabled">
                <span class="page-link">…</span>
            </li>
        `);
    }

    addPage(1);
    if (start > 2) addDots();
    for (let i = start; i <= end; i++) addPage(i);
    if (end < totalPages - 1) addDots();
    if (totalPages > 1) addPage(totalPages);
}
