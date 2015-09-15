gui.calendars = new GuiElement(api.calendars, "imgal")
gui.calendars.link = ->
  "use strict"

  rulesTable = undefined
  clearRules = ->
    if rulesTable
      $tbl = $(rulesTable).dataTable()
      $tbl.fnClearTable()
      $tbl.fnDestroy()
      rulesTable = undefined
    $("#rules-placeholder").empty()
    $("#detail-placeholder").addClass "hidden"
    return

  freqDct =
    'DAILY': [gettext('day'), gettext('days'), gettext('Dayly')]
    'WEEKLY': [gettext('week'), gettext('weeks'), gettext('Weekly')]
    'MONTHLY': [gettext('month'), gettext('months'), gettext('Monthly')]
    'YEARLY': [gettext('year'), gettext('years'), gettext('Yearly')]
    'WEEKDAYS': ['', '', gettext('Weekdays')]

  weekDays = [
    gettext('Sun'), gettext('Monday'), gettext('Tuesday'), gettext('Wednesday'), gettext('Thursday'), gettext('Friday'), gettext('Saturday')
  ]

  renderer = (fld, data, type, record) ->
    # Display "custom" fields of rules table
    if fld == "interval"
      if record.frequency == "WEEKDAYS"
        res = []
        for i in [0..6]
          if data & 1 != 0
            res.push(weekDays[i].substr(0,3))
          data >>= 1
        return res.join(",")
      try
        return data + " " + freqDct[record.frequency][pluralidx(data)]
      catch e
        return e
    else if fld == "duration"
      if data < 60
        return data + " " + gettext('minutes')
      else
        return Math.floor(data/60) + ":" + ("00" + data%60).slice(-2) + " " + gettext("hours")
    return fld
    
  newEditFnc = (forEdit) ->
    realFnc = (value, refreshFnc) ->
      sortFnc = (a, b) ->
        return 1 if a.value > b.value
        return -1 if a.value < b.value
        return 0

      api.templates.get "calendar_rule", (tmpl) ->
        content = api.templates.evaluate(tmpl,
            freqs: ( {id: key, value: val[2]} for own key, val of freqDct)
            days: (w.substr(0, 3) for w in weekDays)
        )
        modalId = gui.launchModal((if value is null then gettext("New rule") else gettext("Edit rule") + ' <b>' + value.name + '</b>' ), content,
          actionButton: "<button type=\"button\" class=\"btn btn-success button-accept\">" + gettext("Save") + "</button>"
        )
        $('#div-interval').show()
        $('#div-weekdays').hide()

        # Fill in fields if needed
        if value != null
            alert('ok')


        # apply styles
        gui.tools.applyCustoms modalId

        # Event handlers

        # Change frequency
        $('#id-rule-freq').on 'change', () ->
          $this = $(this)
          if $this.val() == "WEEKDAYS"
            $('#div-interval').hide()
            $('#div-weekdays').show()
          else
            $('#div-interval').show()
            $('#div-weekdays').hide()
          return

        # Save
        $(modalId + " .button-accept").click ->

          value = { id: '' } if value is null

          values = {}

          $(modalId + ' :input').each ()->
            values[this.name] = $(this).val()
            return

          $(modalId + ' :input[type=checkbox]').each ()->
            gui.doLog this.name, $(this).prop('checked')
            values[this.name] = $(this).prop('checked')
            return

          value.name = values.rule_name

          if $('#id-rule-freq').val() == 'WEEKDAYS'
            value.interval = -1
          else
            value.interval = values.rule_interval

          gui.doLog value, values


    if forEdit is true
      (value, event, table, refreshFnc) ->
        realFnc value, refreshFnc
    else
      (meth, table, refreshFnc) ->
        realFnc null, refreshFnc


  api.templates.get "calendars", (tmpl) ->
    gui.clearWorkspace()
    gui.appendToWorkspace api.templates.evaluate(tmpl,
      calendars: "calendars-placeholder"
      rules: "rules-placeholder"
    )
    gui.calendars.table
      icon: 'calendars'
      container: "calendars-placeholder"
      rowSelect: "single"
      onRowSelect: (selected) ->
        clearRules()
        $("#detail-placeholder").removeClass "hidden"
        # gui.tools.blockUI()
        id = selected[0].id
        rules = new GuiElement(api.calendars.detail(id, "rules", { permission: selected[0].permission }), "rules")
        rulesTable = rules.table(
          icon: 'calendars'
          callback: renderer
          container: "rules-placeholder"
          rowSelect: "single"
          buttons: [
            "new"
            "edit"
            "delete"
            "xls"
          ]
          onLoad: (k) ->
            # gui.tools.unblockUI()
            return # null return
          onNew: newEditFnc false
          onEdit: newEditFnc true

        )
        return

      onRowDeselect: ->
        clearRules()
        return
      buttons: [
        "new"
        "edit"
        "delete"
        "xls"
        "permissions"
      ]
      onNew: gui.methods.typedNew(gui.calendars, gettext("New calendar"), gettext("Calendar creation error"))
      onEdit: gui.methods.typedEdit(gui.calendars, gettext("Edit calendar"), gettext("Calendar saving error"))
      onDelete: gui.methods.del(gui.calendars, gettext("Delete calendar"), gettext("Calendar deletion error"))
