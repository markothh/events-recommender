function formatDateRange(startTs, endTs) {
    const start = new Date(startTs * 1000);
    const end = endTs ? new Date(endTs * 1000) : null;

    const sameDate = end &&
        start.toDateString() === end.toDateString();

    const sameTime = end &&
        start.getHours() === end.getHours() &&
        start.getMinutes() === end.getMinutes();

    let result = start.toLocaleDateString() + " " +
                 start.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});

    if (!end) return result;

    if (!sameDate) {
        result += " — " + end.toLocaleDateString();
    }

    if (!sameTime) {
        result += " — " + end.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    }

    return result;
}

$(function () {
    $.getJSON("/api/event/" + EVENT_ID, function (ev) {

        $("#ev-title").text(ev.title);
        $("#ev-place").text(ev.address || ev.place_name || "Адрес не указан");
        $("#ev-desc").html(ev.description || "<i>Описание отсутствует</i>");

        /* ---------- Теги ---------- */
        if (ev.matched_tags && ev.matched_tags.length) {
            const tagsHtml = ev.matched_tags
                .slice(0, 6)
                .map(t => `<span class="badge bg-secondary me-1">${t}</span>`)
                .join("");

            $("#ev-tags").html(`
                <div class="text-muted mb-1">
                    Схоже с тем, чем вы интересуетесь:
                </div>
                ${tagsHtml}
            `);
        }

        /* ---------- Карусель ---------- */
        const $imgs = $("#ev-images");
        if (!ev.images.length) {
            $imgs.append(`
                <div class="carousel-item active">
                    <div class="bg-secondary text-white d-flex align-items-center justify-content-center"
                         style="height:300px;">
                        Нет изображений
                    </div>
                </div>
            `);
        } else {
            ev.images.forEach((url, idx) => {
                $imgs.append(`
                    <div class="carousel-item ${idx === 0 ? "active" : ""}">
                        <img src="${url}" class="d-block w-100"
                             style="height:300px;object-fit:cover;">
                    </div>
                `);
            });
        }

        /* ---------- Даты ---------- */
        const $dates = $("#ev-dates");
        if (!ev.dates.length) {
            $dates.append("<li class='text-muted'>Нет актуальных дат</li>");
        } else {
            ev.dates.forEach(d => {
                $dates.append(`<li>${formatDateRange(d.start, d.end)}</li>`);
            });
        }

        /* ---------- Карта ---------- */
        if (ev.lat && ev.lon) {
            ymaps.ready(function () {
                const map = new ymaps.Map("ev-map", {
                    center: [ev.lat, ev.lon],
                    zoom: 15
                });

                map.geoObjects.add(
                    new ymaps.Placemark(
                        [ev.lat, ev.lon],
                        { balloonContent: ev.place_name || ev.address || "" }
                    )
                );
            });
        } else {
            $("#ev-map").remove()
        }

        /* ---------- Отслеживать ---------- */
        $("#btn-track").click(function () {
            $.post(`/api/track/${EVENT_ID}`, function () {
                $("#btn-track")
                    .removeClass("btn-outline-primary")
                    .addClass("btn-success")
                    .text("Добавлено в отслеживаемые");
            });
        });

    }).fail(() => {
        $("#event-root").html(
            "<div class='alert alert-danger'>Не удалось загрузить событие</div>"
        );
    });
});

$("#btn-track").click(function () {
    $.post("/api/track/" + EVENT_ID)
        .done(function () {
            $("#btn-track")
                .prop("disabled", true)
                .removeClass("btn-outline-primary")
                .addClass("btn-success")
                .text("В отслеживаемых");

            const toastEl = document.getElementById("trackToast");
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        })
        .fail(function () {
            alert("Не удалось добавить событие");
        });
});

