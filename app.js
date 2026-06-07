(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const state = {
    user: null,
    permissions: {},
    options: {},
    page: "dashboard",
    cache: {},
  };

  const pages = [
    ["dashboard", "首页总看板", "学校、UGC、门店、工作汇总的老板视角"],
    ["schools", "学校作战表", "管理每所学校的攻克进度"],
    ["ugc", "UGC活动看板", "管理活动数据和复盘进度"],
    ["followups", "今日跟进", "逾期、今日、未来 7 天跟进"],
    ["storeReports", "门店日报", "门店经营数据每日填报"],
    ["workSummaries", "工作汇总", "员工每日工作进展"],
    ["monthly", "月度汇总", "月底自动汇总销售和员工进展"],
    ["importExport", "数据导入导出", "CSV 模板、导入和导出"],
    ["users", "员工账号管理", "老板管理员工账号和角色"],
    ["settings", "系统设置", "修改密码和查看数据库位置"],
  ];

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    $("loginForm").addEventListener("submit", login);
    $("logoutBtn").addEventListener("click", logout);
    $("modalCloseBtn").addEventListener("click", closeModal);
    $("modalBackdrop").addEventListener("click", (event) => {
      if (event.target === $("modalBackdrop")) closeModal();
    });
    checkSession();
  }

  async function checkSession() {
    try {
      const me = await api("/api/me", { silent401: true });
      state.user = me.user;
      state.permissions = me.permissions;
      await enterApp();
    } catch {
      showLogin();
    }
  }

  async function login(event) {
    event.preventDefault();
    const payload = {
      username: $("loginUsername").value.trim(),
      password: $("loginPassword").value,
    };
    const data = await api("/api/login", { method: "POST", body: payload });
    state.user = data.user;
    state.permissions = data.permissions;
    await enterApp();
    if (state.user.username === "admin" && !state.user.passwordChanged) {
      toast("老板默认密码仍是 admin123，建议到系统设置里修改。");
    }
  }

  async function logout() {
    await api("/api/logout", { method: "POST" });
    state.user = null;
    state.permissions = {};
    state.cache = {};
    showLogin();
  }

  function showLogin() {
    $("loginScreen").hidden = false;
    $("appShell").hidden = true;
  }

  async function enterApp() {
    $("loginScreen").hidden = true;
    $("appShell").hidden = false;
    $("currentUserText").textContent = `${state.user.name} · ${state.user.roleLabel}`;
    await loadOptions();
    renderNav();
    await go("dashboard");
  }

  async function loadOptions() {
    state.options = await api("/api/options");
  }

  function renderNav() {
    const nav = $("navMenu");
    nav.innerHTML = pages
      .filter(([key]) => key !== "users" || state.permissions.canManageUsers)
      .map(([key, label]) => `<button type="button" data-page="${key}" class="${state.page === key ? "active" : ""}">${label}</button>`)
      .join("");
    nav.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => go(button.dataset.page));
    });
  }

  async function go(page) {
    state.page = page;
    const meta = pages.find(([key]) => key === page) || pages[0];
    $("pageTitle").textContent = meta[1];
    $("pageSubtitle").textContent = meta[2];
    renderNav();
    const renderers = {
      dashboard: renderDashboard,
      schools: renderSchools,
      ugc: renderUgc,
      followups: renderFollowups,
      storeReports: renderStoreReports,
      workSummaries: renderWorkSummaries,
      monthly: renderMonthly,
      importExport: renderImportExport,
      users: renderUsers,
      settings: renderSettings,
    };
    $("pageContent").innerHTML = `<div class="section empty">正在加载...</div>`;
    await renderers[page]();
  }

  async function renderDashboard() {
    const data = await api("/api/dashboard");
    $("pageContent").innerHTML = `
      ${statsSection("学校作战总览", [
        ["学校总数", data.school.schoolTotal],
        ["S级学校数量", data.school.sLevelCount],
        ["企微总人数", data.school.wechatTotal],
        ["成交总人数", data.school.orderTotal],
        ["成交总金额", money(data.school.revenueTotal)],
        ["平均转化率", percent(data.school.averageConversion)],
        ["今日待跟进", data.school.todayFollowups],
        ["逾期未跟进", data.school.overdueFollowups, "danger"],
      ])}
      ${statsSection("UGC 活动总览", [
        ["进行中活动", data.ugc.activeCount],
        ["策划中活动", data.ugc.planningCount],
        ["投稿人数", data.ugc.monthSubmission],
        ["产出内容数", data.ugc.monthContent],
        ["总播放量", numberText(data.ugc.monthViews)],
        ["新增企微", data.ugc.newWechat],
        ["UGC成交金额", money(data.ugc.revenue)],
        ["待复盘活动", data.ugc.reviewOverdue, "danger"],
      ])}
      ${statsSection("今日门店数据", [
        ["新增会员", data.store.todayNewMembers],
        ["线上询单", data.store.todayOnlineInquiries],
        ["线下到店", data.store.todayOfflineVisits],
        ["成交订单", data.store.todayOrders],
        ["今日销售额", money(data.store.todaySales), "primary"],
        ["本月销售额", money(data.store.monthSales), "primary"],
        ["本月成交率", percent(data.store.monthConversion)],
        ["目标完成率", percent(data.store.targetCompletion)],
      ])}
      <section class="section">
        <div class="section-head">
          <div><p class="eyebrow">Work</p><h2>今日工作汇总提交情况</h2></div>
        </div>
        <div class="grid-2" style="padding:18px">
          <div class="mini-card"><strong>已提交</strong><p>${data.work.submitted.length ? data.work.submitted.join("、") : "暂无"}</p></div>
          <div class="mini-card"><strong>未提交</strong><p>${data.work.notSubmitted.length ? data.work.notSubmitted.join("、") : "全部已提交"}</p></div>
        </div>
      </section>
    `;
  }

  function statsSection(title, items) {
    return `
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">Dashboard</p><h2>${esc(title)}</h2></div></div>
        <div class="stats-grid">
          ${items.map(([label, value, tone]) => `<article class="stat-card ${tone || ""}"><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join("")}
        </div>
      </section>
    `;
  }

  async function renderSchools() {
    const data = await api("/api/schools");
    state.cache.schools = data.items;
    renderTablePage({
      title: "学校作战表",
      addText: "新增学校",
      canAdd: state.permissions.canCreate,
      rows: data.items,
      columns: [
        ["学校", (r) => `<div class="title-cell"><strong>${esc(r.school_name)}</strong><span class="muted">${esc(r.school_type)} · ${esc(r.area)} · ${esc(r.address)}</span></div>`],
        ["负责人", "owner_name"],
        ["优先级", (r) => badge(r.priority, r.priority === "S级" ? "red" : "blue")],
        ["推进状态", (r) => badge(r.status, statusTone(r.status))],
        ["企微/成交", (r) => `${r.wechat_count} / ${r.order_count}`],
        ["成交金额", (r) => money(r.revenue)],
        ["转化率", (r) => percent(r.conversion_rate)],
        ["下次跟进", "next_follow_up_time"],
        ["下一步动作", "next_action"],
      ],
      onAdd: () => openSchoolForm(),
      onEdit: (row) => openSchoolForm(row),
      onDelete: (row) => deleteItem(`/api/schools/${row.id}`, `确认删除「${row.school_name}」吗？`),
    });
  }

  async function renderUgc() {
    const data = await api("/api/ugc");
    state.cache.ugc = data.items;
    renderTablePage({
      title: "本亦 UGC 活动看板",
      addText: "新增 UGC 活动",
      canAdd: state.permissions.canCreate,
      rows: data.items,
      columns: [
        ["活动", (r) => `<div class="title-cell"><strong>${esc(r.activity_name)}</strong><span class="muted">${esc(r.school_name || "未关联学校")} · ${esc(r.activity_type)}</span></div>`],
        ["状态", (r) => badge(r.status, statusTone(r.status))],
        ["负责人", "owner_name"],
        ["报名/投稿/内容", (r) => `${r.signup_count} / ${r.submission_count} / ${r.content_count}`],
        ["播放量", (r) => numberText(r.views_count)],
        ["新增企微", "new_wechat_count"],
        ["成交金额", (r) => money(r.revenue)],
        ["下次跟进", "next_follow_up_time"],
        ["下一步", "next_action"],
      ],
      onAdd: () => openUgcForm(),
      onEdit: (row) => openUgcForm(row),
      onDelete: (row) => deleteItem(`/api/ugc/${row.id}`, `确认删除「${row.activity_name}」吗？`),
    });
  }

  async function renderStoreReports(filters = {}) {
    const query = queryString(filters);
    const data = await api(`/api/store-reports${query}`);
    state.cache.storeReports = data.items;
    $("pageContent").innerHTML = filterHtml("门店日报", [
      ["date", "按日期", "date", filters.date || ""],
      ["month", "按月份", "month", filters.month || state.options.month],
    ]);
    $("filterForm").addEventListener("submit", (event) => {
      event.preventDefault();
      renderStoreReports(formToObject(event.target));
    });
    appendTablePage({
      addText: "新增门店日报",
      canAdd: state.user.role !== "viewer",
      rows: data.items,
      columns: [
        ["日期", "report_date"],
        ["门店", "store_name"],
        ["填报人", "reporter_name"],
        ["新增会员", "new_members"],
        ["线上/到店", (r) => `${r.online_inquiries} / ${r.offline_visits}`],
        ["成交订单", "orders_count"],
        ["今日销售额", (r) => money(r.sales_amount)],
        ["成交率", (r) => percent(r.conversion_rate)],
        ["本月累计", (r) => money(r.month_sales_total)],
        ["目标完成", (r) => percent(r.target_completion_rate)],
      ],
      onAdd: () => openStoreForm(),
      onEdit: (row) => openStoreForm(row),
      onDelete: (row) => deleteItem(`/api/store-reports/${row.id}`, `确认删除 ${row.report_date} 的门店日报吗？`),
    });
  }

  async function renderWorkSummaries(filters = {}) {
    const query = queryString(filters);
    const data = await api(`/api/work-summaries${query}`);
    state.cache.workSummaries = data.items;
    const employeeField = state.permissions.canViewAllStaff ? [["employee_id", "按员工", "select", filters.employee_id || "", ownerOptions(true)]] : [];
    $("pageContent").innerHTML = filterHtml("工作汇总", [
      ...employeeField,
      ["date", "按日期", "date", filters.date || ""],
      ["month", "按月份", "month", filters.month || state.options.month],
    ]);
    $("filterForm").addEventListener("submit", (event) => {
      event.preventDefault();
      renderWorkSummaries(formToObject(event.target));
    });
    appendTablePage({
      addText: "新增工作汇总",
      canAdd: state.user.role !== "viewer",
      rows: data.items,
      columns: [
        ["日期", "work_date"],
        ["员工", "employee_name"],
        ["完成事项", "completed_items"],
        ["跟进学校", "followed_schools"],
        ["跟进客户", "follow_customer_count"],
        ["新增企微", "new_wechat_count"],
        ["UGC推进", "ugc_progress"],
        ["明日计划", "tomorrow_plan"],
      ],
      onAdd: () => openWorkForm(),
      onEdit: (row) => openWorkForm(row),
      onDelete: (row) => deleteItem(`/api/work-summaries/${row.id}`, `确认删除 ${row.employee_name} 的工作汇总吗？`),
    });
  }

  async function renderMonthly(month = state.options.month) {
    const data = await api(`/api/monthly-summary?month=${encodeURIComponent(month || state.options.month)}`);
    $("pageContent").innerHTML = `
      <section class="section">
        <div class="section-head">
          <div><p class="eyebrow">Monthly</p><h2>${esc(data.month)} 月度汇总</h2></div>
        </div>
        <form class="toolbar" id="monthForm">
          <label><span>选择月份</span><input name="month" type="month" value="${esc(data.month)}"></label>
          <button class="btn btn-primary" type="submit">查看本月汇总</button>
          <a class="btn btn-ghost" href="/api/export/store-reports?month=${esc(data.month)}">导出门店日报 CSV</a>
          <a class="btn btn-ghost" href="/api/export/work-summaries?month=${esc(data.month)}">导出工作汇总 CSV</a>
        </form>
      </section>
      ${statsSection("本月门店汇总", [
        ["本月总销售额", money(data.store.totalSales), "primary"],
        ["本月成交订单", data.store.totalOrders],
        ["本月线下到店", data.store.totalOfflineVisits],
        ["本月成交率", percent(data.store.conversionRate)],
        ["月度目标完成率", percent(data.store.targetCompletionRate)],
      ])}
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">Employees</p><h2>员工月度工作汇总</h2></div></div>
        ${simpleTable(data.employees, [
          ["员工", "employee_name"],
          ["提交日报天数", "submit_days"],
          ["新增企微数", "new_wechat_count"],
          ["跟进客户数", "follow_customer_count"],
          ["主要完成事项", (r) => (r.completed_items || []).slice(0, 4).join("；")],
          ["UGC推进", (r) => (r.ugc_progress || []).slice(0, 3).join("；")],
        ])}
      </section>
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">UGC</p><h2>本月 UGC 活动推进汇总</h2></div></div>
        <div class="stats-grid">
          ${[
            ["活动数", data.ugc.activityCount],
            ["进行中", data.ugc.activeCount],
            ["投稿数", data.ugc.submissionCount],
            ["内容数", data.ugc.contentCount],
            ["播放量", numberText(data.ugc.viewsCount)],
            ["新增企微", data.ugc.newWechatCount],
          ].map(([label, value]) => `<article class="stat-card"><span>${label}</span><strong>${value}</strong></article>`).join("")}
        </div>
        <ul class="summary-list">${(data.ugc.summary || []).map((item) => `<li>${esc(item)}</li>`).join("") || "<li>暂无 UGC 汇总</li>"}</ul>
      </section>
    `;
    $("monthForm").addEventListener("submit", (event) => {
      event.preventDefault();
      renderMonthly(new FormData(event.target).get("month"));
    });
  }

  async function renderFollowups() {
    const data = await api("/api/followups");
    $("pageContent").innerHTML = `
      <div class="grid-2">
        ${followupBox("逾期未跟进", data.overdue, "red")}
        ${followupBox("今天需要跟进", data.today, "gold")}
      </div>
      <section class="section">${followupBox("未来 7 天需要跟进", data.upcoming, "green", true)}</section>
    `;
  }

  function followupBox(title, rows, tone) {
    return `
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">Follow</p><h2>${esc(title)}</h2></div><span class="badge ${tone}">${rows.length}</span></div>
        <div class="cards-list">
          ${rows.length ? rows.map((r) => `<div class="mini-card"><strong>${esc(r.kind)} · ${esc(r.name)}</strong><p>${esc(r.owner_name)} · ${esc(r.status)} · ${esc(r.next_follow_up_time)}</p><p>${esc(r.next_action || "未填写下一步")}</p></div>`).join("") : `<div class="empty">暂无记录</div>`}
        </div>
      </section>
    `;
  }

  function renderImportExport() {
    const groups = [
      ["schools", "学校作战表", "/api/export/schools", "/api/template/schools", "/api/import/schools"],
      ["ugc", "UGC 活动", "/api/export/ugc", "/api/template/ugc", "/api/import/ugc"],
      ["store", "门店日报", "/api/export/store-reports", "/api/template/store-reports", "/api/import/store-reports"],
      ["work", "工作汇总", "/api/export/work-summaries", "/api/template/work-summaries", "/api/import/work-summaries"],
    ];
    $("pageContent").innerHTML = `
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">CSV</p><h2>数据导入导出</h2></div></div>
        <div class="import-grid">
          ${groups.map(([key, title, exportUrl, tplUrl]) => `
            <div class="import-box">
              <strong>${title}</strong>
              <a class="btn btn-ghost" href="${exportUrl}">导出 CSV</a>
              <a class="btn btn-soft" href="${tplUrl}">下载模板</a>
              ${state.permissions.canImport ? `<input type="file" accept=".csv,text/csv" data-import="${key}"><button class="btn btn-primary" data-import-btn="${key}" type="button">导入 CSV</button>` : `<span class="muted">当前账号没有导入权限</span>`}
            </div>
          `).join("")}
        </div>
      </section>
    `;
    document.querySelectorAll("[data-import-btn]").forEach((button) => {
      button.addEventListener("click", () => importCsv(button.dataset.import));
    });
  }

  async function renderUsers() {
    const data = await api("/api/users");
    const rows = data.items.map((item) => ({ ...item, canEdit: true, canDelete: item.id !== state.user.id }));
    renderTablePage({
      title: "员工账号管理",
      addText: "新增员工账号",
      canAdd: true,
      rows,
      columns: [
        ["姓名", "name"],
        ["账号", "username"],
        ["角色", "roleLabel"],
        ["手机号", "phone"],
        ["状态", (r) => badge(r.status === "enabled" ? "启用" : "停用", r.status === "enabled" ? "green" : "red")],
        ["创建时间", "createdAt"],
        ["最后登录", (r) => r.lastLoginAt || "未登录"],
      ],
      onAdd: () => openUserForm(),
      onEdit: (row) => openUserForm(row),
      onDelete: (row) => deleteItem(`/api/users/${row.id}`, `确认删除员工账号「${row.name}」吗？`),
    });
  }

  function renderSettings() {
    $("pageContent").innerHTML = `
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">Settings</p><h2>系统设置</h2></div></div>
        <form class="modal-form" id="passwordForm">
          <label><span>原密码</span><input name="oldPassword" type="password" required></label>
          <label><span>新密码</span><input name="newPassword" type="password" required minlength="6"></label>
          <div class="modal-actions"><button class="btn btn-primary" type="submit">修改密码</button></div>
        </form>
      </section>
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">Database</p><h2>数据库位置</h2></div></div>
        <div class="cards-list"><div class="mini-card"><strong>${esc(state.options.dbPath)}</strong><p>所有后台数据都保存在这个 SQLite 文件里。</p></div></div>
      </section>
    `;
    $("passwordForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      await api("/api/me/password", { method: "PUT", body: formToObject(event.target) });
      toast("密码已修改");
      event.target.reset();
    });
  }

  function renderTablePage(config) {
    $("pageContent").innerHTML = `<section class="section" id="tableSection"></section>`;
    appendTablePage(config);
  }

  function appendTablePage(config) {
    const target = $("tableSection") || document.createElement("section");
    target.className = "section";
    target.innerHTML = `
      <div class="section-head">
        <div><p class="eyebrow">Data</p><h2>${esc(config.title || $("pageTitle").textContent)}</h2></div>
        <div>${config.canAdd ? `<button class="btn btn-primary" id="addRowBtn" type="button">${esc(config.addText || "新增")}</button>` : ""}</div>
      </div>
      ${simpleTable(config.rows, config.columns, config)}
    `;
    if (!target.parentNode) $("pageContent").appendChild(target);
    const add = $("addRowBtn");
    if (add) add.addEventListener("click", config.onAdd);
    target.querySelectorAll("[data-edit]").forEach((btn) => btn.addEventListener("click", () => config.onEdit(config.rows.find((r) => String(r.id) === btn.dataset.edit))));
    target.querySelectorAll("[data-delete]").forEach((btn) => btn.addEventListener("click", () => config.onDelete(config.rows.find((r) => String(r.id) === btn.dataset.delete))));
  }

  function simpleTable(rows, columns, config = {}) {
    if (!rows.length) return `<div class="empty">暂无数据</div>`;
    return `
      <div class="table-wrap">
        <table>
          <thead><tr>${columns.map(([label]) => `<th>${esc(label)}</th>`).join("")}${config.onEdit || config.onDelete ? "<th>操作</th>" : ""}</tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                ${columns.map(([, field]) => `<td>${renderCell(row, field)}</td>`).join("")}
                ${config.onEdit || config.onDelete ? `<td><div class="row-actions">${row.canEdit && config.onEdit ? `<button class="btn btn-ghost btn-small" data-edit="${row.id}" type="button">编辑</button>` : ""}${row.canDelete && config.onDelete ? `<button class="btn btn-danger btn-small" data-delete="${row.id}" type="button">删除</button>` : ""}</div></td>` : ""}
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderCell(row, field) {
    if (typeof field === "function") return field(row);
    return esc(row[field] ?? "");
  }

  function filterHtml(title, fields) {
    return `
      <section class="section">
        <div class="section-head"><div><p class="eyebrow">Filter</p><h2>${esc(title)}</h2></div></div>
        <form class="filters" id="filterForm">
          ${fields.map(([name, label, type, value, options]) => fieldHtml({ name, label, type, value, options })).join("")}
          <label><span>&nbsp;</span><button class="btn btn-primary" type="submit">筛选</button></label>
        </form>
      </section>
      <section class="section" id="tableSection"></section>
    `;
  }

  function openSchoolForm(row = {}) {
    openForm({
      title: row.id ? "编辑学校" : "新增学校",
      fields: [
        f("school_name", "学校名称", "text", row.school_name, true),
        f("school_type", "学校类型", "select", row.school_type, true, state.options.schoolTypes),
        f("area", "区域", "text", row.area || "朝阳市"),
        f("address", "地址", "text", row.address),
        f("student_count", "学生规模", "number", row.student_count),
        f("owner_id", "负责人", "select", row.owner_id, true, ownerOptions()),
        f("priority", "优先级", "select", row.priority, true, state.options.schoolPriorities),
        f("status", "当前推进状态", "select", row.status, true, state.options.schoolStatuses),
        f("wechat_count", "企微人数", "number", row.wechat_count),
        f("trial_count", "到店试穿人数", "number", row.trial_count),
        f("order_count", "成交人数", "number", row.order_count),
        f("revenue", "成交金额", "number", row.revenue),
        f("main_product", "主推品类", "select", row.main_product, false, state.options.mainProducts),
        f("main_sizes", "主流尺码", "text", row.main_sizes),
        f("next_follow_up_time", "下次跟进时间", "date", row.next_follow_up_time),
        f("next_action", "下一步动作", "text", row.next_action, false, null, true),
        f("notes", "备注", "textarea", row.notes, false, null, true),
      ],
      submit: async (data) => {
        await saveRow(row.id ? `/api/schools/${row.id}` : "/api/schools", row.id ? "PUT" : "POST", data);
        await loadOptions();
        await renderSchools();
      },
    });
  }

  function openUgcForm(row = {}) {
    openForm({
      title: row.id ? "编辑 UGC 活动" : "新增 UGC 活动",
      fields: [
        f("activity_name", "活动名称", "text", row.activity_name, true),
        f("school_id", "对应学校", "select", row.school_id, false, schoolOptions(true)),
        f("activity_type", "活动类型", "select", row.activity_type, true, state.options.ugcTypes),
        f("status", "活动状态", "select", row.status, true, state.options.ugcStatuses),
        f("goal", "活动目标", "text", row.goal, false, null, true),
        f("start_date", "活动开始日期", "date", row.start_date),
        f("end_date", "活动结束日期", "date", row.end_date),
        f("owner_id", "负责人", "select", row.owner_id, true, ownerOptions()),
        f("budget", "预算", "number", row.budget),
        f("signup_count", "报名人数", "number", row.signup_count),
        f("submission_count", "投稿人数", "number", row.submission_count),
        f("content_count", "产出内容数", "number", row.content_count),
        f("views_count", "总播放量", "number", row.views_count),
        f("likes_count", "总点赞量", "number", row.likes_count),
        f("comments_count", "总评论量", "number", row.comments_count),
        f("new_wechat_count", "新增企微人数", "number", row.new_wechat_count),
        f("order_count", "带来成交人数", "number", row.order_count),
        f("revenue", "带来成交金额", "number", row.revenue),
        f("next_follow_up_time", "下次跟进时间", "date", row.next_follow_up_time),
        f("current_issue", "当前问题", "textarea", row.current_issue, false, null, true),
        f("next_action", "下一步动作", "textarea", row.next_action, false, null, true),
        f("review_summary", "复盘结论", "textarea", row.review_summary, false, null, true),
      ],
      submit: async (data) => {
        await saveRow(row.id ? `/api/ugc/${row.id}` : "/api/ugc", row.id ? "PUT" : "POST", data);
        await loadOptions();
        await renderUgc();
      },
    });
  }

  function openStoreForm(row = {}) {
    openForm({
      title: row.id ? "编辑门店日报" : "新增门店日报",
      fields: [
        f("report_date", "日期", "date", row.report_date || state.options.today, true),
        f("store_name", "门店", "text", row.store_name || "本亦门店", true),
        f("reporter_id", "填报人", "select", row.reporter_id || state.user.id, true, reporterOptions()),
        f("new_members", "新增会员", "number", row.new_members),
        f("online_inquiries", "线上询单", "number", row.online_inquiries),
        f("offline_visits", "线下到店", "number", row.offline_visits),
        f("orders_count", "成交订单", "number", row.orders_count),
        f("sales_amount", "今日销售额", "number", row.sales_amount),
        f("monthly_sales_target", "月度销售目标", "number", row.monthly_sales_target),
        f("notes", "备注", "textarea", row.notes, false, null, true),
      ],
      submit: async (data) => {
        await saveRow(row.id ? `/api/store-reports/${row.id}` : "/api/store-reports", row.id ? "PUT" : "POST", data);
        await renderStoreReports({ month: data.report_date ? data.report_date.slice(0, 7) : state.options.month });
      },
    });
  }

  function openWorkForm(row = {}) {
    openForm({
      title: row.id ? "编辑工作汇总" : "新增工作汇总",
      fields: [
        f("work_date", "日期", "date", row.work_date || state.options.today, true),
        f("employee_id", "员工姓名", "select", row.employee_id || state.user.id, true, workEmployeeOptions()),
        f("completed_items", "今日完成事项", "textarea", row.completed_items, true, null, true),
        f("followed_schools", "跟进学校", "text", row.followed_schools),
        f("follow_customer_count", "跟进客户数", "number", row.follow_customer_count),
        f("new_wechat_count", "新增企微数", "number", row.new_wechat_count),
        f("ugc_progress", "UGC推进情况", "textarea", row.ugc_progress, false, null, true),
        f("issues", "遇到问题", "textarea", row.issues, false, null, true),
        f("tomorrow_plan", "明日计划", "textarea", row.tomorrow_plan, false, null, true),
        f("need_boss_support", "需要老板协调事项", "textarea", row.need_boss_support, false, null, true),
      ],
      submit: async (data) => {
        await saveRow(row.id ? `/api/work-summaries/${row.id}` : "/api/work-summaries", row.id ? "PUT" : "POST", data);
        await renderWorkSummaries({ month: data.work_date ? data.work_date.slice(0, 7) : state.options.month });
      },
    });
  }

  function openUserForm(row = {}) {
    openForm({
      title: row.id ? "编辑员工账号" : "新增员工账号",
      fields: [
        f("name", "姓名", "text", row.name, true),
        f("username", "账号", "text", row.username, !row.id),
        f("role", "角色", "select", row.role || "viewer", true, state.options.roles.map((r) => ({ value: r.value, label: r.label }))),
        f("phone", "手机号", "text", row.phone),
        f("status", "状态", "select", row.status || "enabled", true, [{ value: "enabled", label: "启用" }, { value: "disabled", label: "停用" }]),
        f("password", row.id ? "重置密码（不填则不改）" : "初始密码", "password", ""),
      ],
      submit: async (data) => {
        await saveRow(row.id ? `/api/users/${row.id}` : "/api/users", row.id ? "PUT" : "POST", data);
        await loadOptions();
        await renderUsers();
      },
    });
  }

  function openForm({ title, fields, submit }) {
    $("modalTitle").textContent = title;
    $("modalForm").innerHTML = `
      ${fields.map(fieldHtml).join("")}
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" id="cancelModalBtn">取消</button>
        <button class="btn btn-primary" type="submit">保存</button>
      </div>
    `;
    $("modalBackdrop").hidden = false;
    $("cancelModalBtn").addEventListener("click", closeModal);
    $("modalForm").onsubmit = async (event) => {
      event.preventDefault();
      await submit(formToObject(event.target));
      closeModal();
      toast("已保存");
    };
  }

  function closeModal() {
    $("modalBackdrop").hidden = true;
    $("modalForm").innerHTML = "";
  }

  function fieldHtml(field) {
    const value = field.value ?? "";
    const full = field.full ? "full" : "";
    const required = field.required ? "required" : "";
    if (field.type === "select") {
      return `<label class="${full}"><span>${esc(field.label)}${field.required ? " *" : ""}</span><select name="${field.name}" ${required}>${(field.options || []).map((opt) => {
        const item = typeof opt === "string" ? { value: opt, label: opt } : opt;
        return `<option value="${esc(item.value)}" ${String(item.value) === String(value) ? "selected" : ""}>${esc(item.label)}</option>`;
      }).join("")}</select></label>`;
    }
    if (field.type === "textarea") {
      return `<label class="${full}"><span>${esc(field.label)}${field.required ? " *" : ""}</span><textarea name="${field.name}" ${required}>${esc(value)}</textarea></label>`;
    }
    return `<label class="${full}"><span>${esc(field.label)}${field.required ? " *" : ""}</span><input name="${field.name}" type="${field.type || "text"}" value="${esc(value)}" ${required}></label>`;
  }

  function f(name, label, type, value, required = false, options = null, full = false) {
    return { name, label, type, value, required, options, full };
  }

  async function saveRow(url, method, data) {
    await api(url, { method, body: data });
  }

  async function deleteItem(url, message) {
    if (!window.confirm(message)) return;
    await api(url, { method: "DELETE" });
    toast("已删除");
    await go(state.page);
  }

  async function importCsv(kind) {
    const input = document.querySelector(`[data-import="${kind}"]`);
    const file = input.files && input.files[0];
    if (!file) {
      toast("请先选择 CSV 文件");
      return;
    }
    const text = await file.text();
    const endpoints = {
      schools: "/api/import/schools",
      ugc: "/api/import/ugc",
      store: "/api/import/store-reports",
      work: "/api/import/work-summaries",
    };
    const result = await api(endpoints[kind], { method: "POST", body: { csv: text } });
    toast(`导入完成：${result.created} 条`);
  }

  function ownerOptions(includeAll = false) {
    const items = (state.options.owners || []).map((u) => ({ value: u.id, label: `${u.name} · ${u.roleLabel}` }));
    return includeAll ? [{ value: "", label: "全部员工" }, ...items] : items;
  }

  function reporterOptions() {
    if (["admin", "operation_manager", "clerk"].includes(state.user.role)) return ownerOptions();
    return [{ value: state.user.id, label: state.user.name }];
  }

  function workEmployeeOptions() {
    if (["admin", "operation_manager"].includes(state.user.role)) return ownerOptions();
    return [{ value: state.user.id, label: state.user.name }];
  }

  function schoolOptions(includeBlank = false) {
    const items = (state.options.schools || []).map((s) => ({ value: s.id, label: s.name }));
    return includeBlank ? [{ value: "", label: "不关联学校" }, ...items] : items;
  }

  function formToObject(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  async function api(path, options = {}) {
    const init = { method: options.method || "GET", headers: {}, credentials: "same-origin" };
    if (options.body) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    const response = await fetch(path, init);
    const contentType = response.headers.get("Content-Type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      if (response.status === 401 && !options.silent401) showLogin();
      const message = data.error || "请求失败";
      if (!options.silent401) toast(message);
      throw new Error(message);
    }
    return data;
  }

  function queryString(filters) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const text = params.toString();
    return text ? `?${text}` : "";
  }

  function badge(text, tone = "") {
    return `<span class="badge ${tone}">${esc(text)}</span>`;
  }

  function statusTone(value) {
    if (["进行中", "已成交", "已加企微", "已到店试穿"].includes(value)) return "green";
    if (["策划中", "预热中", "已整理资料", "已发内容"].includes(value)) return "blue";
    if (["复盘中", "物料准备中", "评论区有反馈"].includes(value)) return "gold";
    if (["暂停"].includes(value)) return "red";
    return "";
  }

  function money(value) {
    if (value === null || value === undefined) return "无权限";
    return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  function percent(value) {
    if (value === null || value === undefined) return "无权限";
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
  }

  function numberText(value) {
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
  }

  function toast(message) {
    $("toast").textContent = message;
    $("toast").hidden = false;
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => {
      $("toast").hidden = true;
    }, 2600);
  }
})();
