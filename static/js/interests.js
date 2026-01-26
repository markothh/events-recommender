$(function () {
  const container = $("#tags-container");
  let tags = [];
  let selected = new Set();

  function render() {
    container.empty();

    tags.forEach(t => {
      const el = $(`<div class="badge tag-tile p-2">${t.name}</div>`);
      el.data("id", t.id);

      if (selected.has(t.id)) {
        el.addClass("tag-selected");
      }

      el.on("click", function () {
        const id = $(this).data("id");

        if (selected.has(id)) {
          selected.delete(id);
          $(this).removeClass("tag-selected");
        } else {
          selected.add(id);
          $(this).addClass("tag-selected");
        }
      });

      container.append(el);
    });
  }

  $.getJSON("/api/tags").done(function (data) {
    tags = data;
    render();
  });

  $("#save-interests").on("click", function () {
    const arr = Array.from(selected);

    $.ajax({
      url: "/select-interests",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ selected: arr })
    }).done(function () {
      // немедленный переход на главную
      window.location.href = "/";
    });
  });
});
