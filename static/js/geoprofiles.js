let selectedLat = null;
let selectedLon = null;
let map;
let placemark;

$(function () {
    loadProfiles();

    $("#createProfileModal").on("shown.bs.modal", initCreateMap);
    $("#btn-save-profile").on("click", saveProfile);
});

function loadProfiles() {
    $.getJSON("/api/geoprofiles", function (profiles) {
        const $list = $("#profiles-list");
        $list.empty();

        $.getJSON("/api/geoprofiles/active", function (activeId) {

            const isActiveCurrent = !activeId;
            $list.append(renderCurrentLocationProfile(isActiveCurrent));

            profiles.forEach(p => {
                const isActive = activeId === p.id;
                $list.append(renderProfileCard(p, isActive));
            });
        });
    });
}

function renderCurrentLocationProfile(isActive) {
    const $card = $(`
    <div class="col-md-4">
      <div class="card h-100 profile-card ${isActive ? "border-primary" : ""}" style="cursor:pointer">
        <div class="card-body">
          <h6 class="card-title">Текущая позиция</h6>
          <p class="text-muted small">Используется геолокация браузера</p>
        </div>
      </div>
    </div>
    `);

    $card.find(".profile-card").click(() => {
        $.ajax({
            url: "/api/geoprofiles/active",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ active_profile_id: null }),
            success: function () {
                $(".profile-card").removeClass("border-primary");
                $card.find(".profile-card").addClass("border-primary");
            }
        });
    });

    return $card;
}

function renderProfileCard(p, isActive) {
    const $card = $(`
    <div class="col-md-4">
      <div class="card h-100 profile-card ${isActive ? "border-primary" : ""}" data-id="${p.id}" style="cursor:pointer; position: relative;">
        <div class="card-body">
          <h6 class="card-title">${p.name}</h6>
          <p class="text-muted small" id="addr-${p.id}">Загрузка адреса...</p>
          <button class="btn btn-sm btn-secondary delete-profile" style="position: absolute; top: 8px; right: 8px;">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </div>`);

    // Reverse geocoding
    ymaps.ready(() => {
        ymaps.geocode([p.lat, p.lon]).then(res => {
            const firstGeoObject = res.geoObjects.get(0);
            if (firstGeoObject) {
                $(`#addr-${p.id}`).text(firstGeoObject.getAddressLine());
            } else {
                $(`#addr-${p.id}`).text("Адрес не найден");
            }
        });
    });

    // Клик по профилю = переключение
    $card.find(".profile-card").click((e) => {
        if ($(e.target).closest(".delete-profile").length) return; // не переключаем при клике на удаление

        const profileId = p.id;

        $.ajax({
            url: "/api/geoprofiles/active",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ active_profile_id: profileId }),
            success: function () {
                $(".profile-card").removeClass("border-primary");
                $card.find(".profile-card").addClass("border-primary");
            }
        });
    });

    // Кнопка удаления
    $card.find(".delete-profile").click(() => {
        if (!confirm(`Удалить профиль "${p.name}"?`)) return;

        $.ajax({
            url: `/api/geoprofiles/${p.id}`,
            method: "DELETE",
            success: function () {
                loadProfiles();
            },
            error: function () {
                alert("Ошибка при удалении профиля");
            }
        });
    });

    return $card;
}

/* ---------- Карта в форме создания ---------- */

function initCreateMap() {
    if (map) return;

    ymaps.ready(() => {
        map = new ymaps.Map("profile-map", {
            center: [55.751244, 37.618423],
            zoom: 9
        });

        map.events.add("click", e => {
            const coords = e.get("coords");
            selectedLat = coords[0];
            selectedLon = coords[1];

            if (placemark) {
                placemark.geometry.setCoordinates(coords);
            } else {
                placemark = new ymaps.Placemark(coords);
                map.geoObjects.add(placemark);
            }
        });
    });
}

/* ---------- Сохранение нового профиля ---------- */

function saveProfile() {
    const name = $("#profile-name").val().trim();

    if (!name || selectedLat === null) {
        alert("Укажите название и точку на карте");
        return;
    }

    $.ajax({
        url: "/api/geoprofiles",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            name: name,
            lat: selectedLat,
            lon: selectedLon
        }),
        success: function () {
            $("#createProfileModal").modal("hide");
            $("#profile-name").val("");
            selectedLat = selectedLon = null;
            loadProfiles();
        }
    });
}
