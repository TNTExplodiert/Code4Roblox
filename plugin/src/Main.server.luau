local PluginHandle = plugin

local AgentClient = require(script.Plugin.AgentClient)
local OperationApplier = require(script.Plugin.OperationApplier)
local Settings = require(script.Plugin.Settings)
local SnapshotBuilder = require(script.Plugin.SnapshotBuilder)
local OperationPreview = require(script.Shared.OperationPreview)
local Protocol = require(script.Shared.Protocol)

local state = {
    agentUrl = Settings.get(PluginHandle, 'agent_url', 'http://127.0.0.1:8787'),
    projectRoot = Settings.get(PluginHandle, 'project_root', ''),
    sessionId = Settings.get(PluginHandle, 'session_id', nil),
    polling = false,
    pendingBatch = nil,
}

local toolbar = PluginHandle:CreateToolbar('CodeRoblox')
local toggleButton = toolbar:CreateButton('CodeRoblox', 'Open the CodeRoblox control panel.', '')

local widgetInfo =
    DockWidgetPluginGuiInfo.new(Enum.InitialDockState.Left, true, false, 420, 460, 360, 360)

local widget = PluginHandle:CreateDockWidgetPluginGui('CodeRobloxWidget', widgetInfo)
widget.Title = 'CodeRoblox'

local root = Instance.new('Frame')
root.Name = 'Root'
root.Size = UDim2.fromScale(1, 1)
root.BackgroundTransparency = 1
root.Parent = widget

local layout = Instance.new('UIListLayout')
layout.Padding = UDim.new(0, 8)
layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
layout.VerticalAlignment = Enum.VerticalAlignment.Top
layout.FillDirection = Enum.FillDirection.Vertical
layout.Parent = root

local padding = Instance.new('UIPadding')
padding.PaddingTop = UDim.new(0, 12)
padding.PaddingLeft = UDim.new(0, 12)
padding.PaddingRight = UDim.new(0, 12)
padding.PaddingBottom = UDim.new(0, 12)
padding.Parent = root

local title = Instance.new('TextLabel')
title.Size = UDim2.new(1, 0, 0, 28)
title.BackgroundTransparency = 1
title.TextXAlignment = Enum.TextXAlignment.Left
title.Font = Enum.Font.BuilderSansBold
title.TextSize = 20
title.Text = 'CodeRoblox Review Console'
title.Parent = root

local statusLabel = Instance.new('TextLabel')
statusLabel.Size = UDim2.new(1, 0, 0, 44)
statusLabel.BackgroundTransparency = 1
statusLabel.TextWrapped = true
statusLabel.TextXAlignment = Enum.TextXAlignment.Left
statusLabel.TextYAlignment = Enum.TextYAlignment.Top
statusLabel.Font = Enum.Font.BuilderSans
statusLabel.TextSize = 16
statusLabel.Text = 'Not connected'
statusLabel.Parent = root

local agentUrlBox = Instance.new('TextBox')
agentUrlBox.Size = UDim2.new(1, 0, 0, 32)
agentUrlBox.ClearTextOnFocus = false
agentUrlBox.Font = Enum.Font.Code
agentUrlBox.PlaceholderText = 'http://127.0.0.1:8787'
agentUrlBox.Text = state.agentUrl
agentUrlBox.TextSize = 14
agentUrlBox.Parent = root

local actions = Instance.new('Frame')
actions.Size = UDim2.new(1, 0, 0, 156)
actions.BackgroundTransparency = 1
actions.Parent = root

local actionsLayout = Instance.new('UIListLayout')
actionsLayout.Padding = UDim.new(0, 6)
actionsLayout.FillDirection = Enum.FillDirection.Vertical
actionsLayout.Parent = actions

local function makeButton(label)
    local button = Instance.new('TextButton')
    button.Size = UDim2.new(1, 0, 0, 28)
    button.AutoButtonColor = true
    button.Font = Enum.Font.BuilderSans
    button.TextSize = 15
    button.Text = label
    button.Parent = actions
    return button
end

local connectButton = makeButton('Connect Session')
local syncButton = makeButton('Sync Studio Context')
local checkpointButton = makeButton('Create Checkpoint')
local approveButton = makeButton('Approve Pending Plan')
local rejectButton = makeButton('Reject Pending Plan')

local previewTitle = Instance.new('TextLabel')
previewTitle.Size = UDim2.new(1, 0, 0, 24)
previewTitle.BackgroundTransparency = 1
previewTitle.TextXAlignment = Enum.TextXAlignment.Left
previewTitle.Font = Enum.Font.BuilderSansBold
previewTitle.TextSize = 16
previewTitle.Text = 'Pending Plan'
previewTitle.Parent = root

local previewBox = Instance.new('TextLabel')
previewBox.Size = UDim2.new(1, 0, 0, 180)
previewBox.BackgroundColor3 = Color3.fromRGB(32, 35, 40)
previewBox.BorderSizePixel = 0
previewBox.TextColor3 = Color3.fromRGB(235, 235, 235)
previewBox.TextWrapped = true
previewBox.TextXAlignment = Enum.TextXAlignment.Left
previewBox.TextYAlignment = Enum.TextYAlignment.Top
previewBox.Font = Enum.Font.Code
previewBox.TextSize = 14
previewBox.Text = 'No pending plan.'
previewBox.Parent = root

local previewPadding = Instance.new('UIPadding')
previewPadding.PaddingTop = UDim.new(0, 8)
previewPadding.PaddingLeft = UDim.new(0, 8)
previewPadding.PaddingRight = UDim.new(0, 8)
previewPadding.PaddingBottom = UDim.new(0, 8)
previewPadding.Parent = previewBox

local function setStatus(message)
    statusLabel.Text = message
end

local function makeClient()
    return AgentClient.new(state.agentUrl)
end

local function setButtonEnabled(button, enabled)
    button.Active = enabled
    button.AutoButtonColor = enabled
    button.TextTransparency = enabled and 0 or 0.45
    button.BackgroundTransparency = enabled and 0 or 0.25
end

local function setPendingBatch(batch)
    state.pendingBatch = batch
    local hasPending = batch ~= nil
    setButtonEnabled(approveButton, hasPending)
    setButtonEnabled(rejectButton, hasPending)
end

local function ensureProjectRoot()
    if state.projectRoot == nil or state.projectRoot == '' then
        state.projectRoot = game.Name
        Settings.set(PluginHandle, 'project_root', state.projectRoot)
    end
end

local function renderBatchPreview(batch)
    if batch == nil then
        previewBox.Text = 'No pending plan.'
        return
    end

    local summary = OperationPreview.summarize(batch.operations, Protocol)
    local lines = {
        string.format('Batch: %s', batch.batch_id),
        string.format(
            'Ops: %d | Low: %d | Medium: %d | High: %d | Destructive: %d',
            summary.total,
            summary.low,
            summary.medium,
            summary.high,
            summary.destructive
        ),
        string.format('Approval required: %s', batch.requires_approval and 'yes' or 'no'),
        '',
    }

    for index, operation in ipairs(batch.operations) do
        if index > 5 then
            table.insert(lines, string.format('... %d more operations', #batch.operations - 5))
            break
        end

        table.insert(
            lines,
            string.format(
                '%d. [%s] %s -> %s',
                index,
                Protocol.riskForKind(operation.kind),
                operation.kind,
                operation.target_path ~= '' and operation.target_path or '<session>'
            )
        )
    end

    previewBox.Text = table.concat(lines, '\n')
end

local function ensureSession()
    ensureProjectRoot()

    if state.sessionId ~= nil and state.sessionId ~= '' then
        return state.sessionId
    end

    local response = makeClient():startSession({
        client_name = 'roblox-studio-plugin',
        project_root = state.projectRoot,
        capabilities = {
            snapshot_overview = true,
            script_documents = true,
            queue_polling = true,
            approval_gate = true,
            apply_script_patch = true,
            create_instance = true,
            update_properties = true,
            reparent_instance = true,
            delete_instance = true,
        },
    })

    state.sessionId = response.session_id
    Settings.set(PluginHandle, 'session_id', state.sessionId)
    return state.sessionId
end

local function pushSnapshot()
    local sessionId = ensureSession()
    local snapshot = SnapshotBuilder.buildSnapshot()
    makeClient():pushSnapshot(sessionId, snapshot)
    setStatus(string.format('Studio context synced for %s', sessionId))
end

local function refreshPendingBatch()
    if state.sessionId == nil or state.sessionId == '' then
        setPendingBatch(nil)
        renderBatchPreview(nil)
        return
    end

    local response = makeClient():getPendingBatch(state.sessionId)
    setPendingBatch(response.batch)
    renderBatchPreview(response.batch)
end

local function pollLoop()
    if state.polling then
        return
    end

    state.polling = true
    task.spawn(function()
        while state.polling do
            if state.sessionId ~= nil and state.sessionId ~= '' then
                if state.pendingBatch == nil then
                    local pendingOk, pendingResponse = pcall(function()
                        return makeClient():getPendingBatch(state.sessionId)
                    end)

                    if pendingOk and pendingResponse ~= nil and pendingResponse.batch ~= nil then
                        setPendingBatch(pendingResponse.batch)
                        renderBatchPreview(pendingResponse.batch)
                        setStatus(
                            string.format(
                                'Pending review for batch %s',
                                pendingResponse.batch.batch_id
                            )
                        )
                    elseif not pendingOk then
                        setStatus(string.format('Pending-plan lookup failed: %s', pendingResponse))
                    end
                end

                if state.pendingBatch == nil then
                    local ok, batch = pcall(function()
                        return makeClient():nextBatch(state.sessionId)
                    end)

                    if ok and batch ~= nil and batch.batch ~= nil then
                        local batchPayload = batch.batch
                        local outcomes = OperationApplier.applyBatch(batchPayload.operations)
                        local success, result = pcall(function()
                            return makeClient():reportBatchResult(
                                state.sessionId,
                                batchPayload.batch_id,
                                outcomes
                            )
                        end)
                        if success then
                            local syncOk, syncErr = pcall(pushSnapshot)
                            if syncOk then
                                setStatus(
                                    string.format(
                                        'Applied batch %s (%s)',
                                        batchPayload.batch_id,
                                        result.batch.status
                                    )
                                )
                            else
                                setStatus(
                                    string.format(
                                        'Applied batch %s, but context sync failed: %s',
                                        batchPayload.batch_id,
                                        syncErr
                                    )
                                )
                            end
                        else
                            setStatus(string.format('Failed to report batch result: %s', result))
                        end
                    elseif not ok then
                        setStatus(string.format('Polling failed: %s', batch))
                    end
                end
            end
            task.wait(2)
        end
    end)
end

setPendingBatch(nil)

toggleButton.Click:Connect(function()
    widget.Enabled = not widget.Enabled
end)

agentUrlBox.FocusLost:Connect(function(enterPressed)
    if not enterPressed then
        return
    end

    state.agentUrl = agentUrlBox.Text
    Settings.set(PluginHandle, 'agent_url', state.agentUrl)
    setStatus(string.format('Agent URL set to %s', state.agentUrl))
end)

connectButton.MouseButton1Click:Connect(function()
    local ok, result = pcall(function()
        local sessionId = ensureSession()
        pushSnapshot()
        refreshPendingBatch()
        return sessionId
    end)

    if ok then
        setStatus(string.format('Connected as %s', result))
        pollLoop()
    else
        setStatus(string.format('Connect failed: %s', result))
    end
end)

syncButton.MouseButton1Click:Connect(function()
    local ok, err = pcall(function()
        pushSnapshot()
        refreshPendingBatch()
    end)
    if not ok then
        setStatus(string.format('Context sync failed: %s', err))
    end
end)

checkpointButton.MouseButton1Click:Connect(function()
    local ok, result = pcall(function()
        local sessionId = ensureSession()
        local response = makeClient():createCheckpoint(sessionId, 'manual-plugin-checkpoint')
        return response.checkpoint.checkpoint_id
    end)

    if ok then
        setStatus(string.format('Checkpoint created: %s', result))
    else
        setStatus(string.format('Checkpoint failed: %s', result))
    end
end)

approveButton.MouseButton1Click:Connect(function()
    if state.pendingBatch == nil then
        return
    end

    local ok, result = pcall(function()
        return makeClient():approveBatch(
            state.sessionId,
            state.pendingBatch.batch_id,
            'approved in Roblox Studio plugin'
        )
    end)

    if ok then
        setPendingBatch(nil)
        renderBatchPreview(nil)
        setStatus(string.format('Approved batch %s', result.batch.batch_id))
    else
        setStatus(string.format('Approval failed: %s', result))
    end
end)

rejectButton.MouseButton1Click:Connect(function()
    if state.pendingBatch == nil then
        return
    end

    local ok, result = pcall(function()
        return makeClient():rejectBatch(
            state.sessionId,
            state.pendingBatch.batch_id,
            'rejected in Roblox Studio plugin'
        )
    end)

    if ok then
        setPendingBatch(nil)
        renderBatchPreview(nil)
        setStatus(string.format('Rejected batch %s', result.batch.batch_id))
    else
        setStatus(string.format('Reject failed: %s', result))
    end
end)
