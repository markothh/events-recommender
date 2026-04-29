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
        // 4 карточки в ряд на PC, 2 на планшете, 1 на мобильном
        if (idx % 4 === 0) {
            row = $('<div class="row g-3 mb-3"></div>');
            $recs.append(row);
        }

        const matchedTags = (event.matched_tags || [])
            .map(t => `<span class="badge bg-secondary me-1">${t}</span>`)
            .join(" ");

        const card = $(`
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card h-100 shadow-sm text-white position-relative" 
                     style="cursor: pointer; border-radius: 8px; overflow: hidden; min-height: 200px; background: ${event.thumbnail ? `url(${event.thumbnail}) center/cover` : '#6c757d'};">

                    <div class="position-absolute top-0 start-0 w-100 p-2" style="background: linear-gradient(to bottom, rgba(0,0,0,0.7), transparent);">
                        <div class="text-truncate fw-semibold">${event.title}</div>
                    </div>

                    <div class="position-absolute bottom-0 start-0 w-100 p-2" style="background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);">
                        ${event.place ? `<div class="small text-truncate"><i class="bi bi-geo-alt"></i> ${event.place}</div>` : ''}
                        ${matchedTags ? `<div class="mt-1">${matchedTags}</div>` : ''}
                    </div>
                </div>
            </div>
        `);

        card.click(function() {
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
