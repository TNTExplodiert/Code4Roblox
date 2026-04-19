local ChangeHistoryService = game:GetService('ChangeHistoryService')
local ScriptEditorService = game:GetService('ScriptEditorService')
local TestService = game:GetService('TestService')

local InstancePath = require(script.Parent.InstancePath)

local OperationApplier = {}
local appliedCheckpoints = {}

local function isMutating(kind)
    return kind == 'apply_script_patch'
        or kind == 'create_instance'
        or kind == 'update_properties'
        or kind == 'reparent_instance'
        or kind == 'delete_instance'
        or kind == 'create_checkpoint'
        or kind == 'rollback_checkpoint'
end

local function createOutcome(operationId, success, message, changedPaths)
    return {
        operation_id = operationId,
        success = success,
        message = message,
        changed_paths = changedPaths or {},
    }
end

local function applyScriptPatch(operation)
    local target = InstancePath.findByPath(operation.target_path)
    if target == nil or not target:IsA('LuaSourceContainer') then
        return createOutcome(operation.operation_id, false, 'Script target not found.', {})
    end

    local expectedSource = operation.preconditions.expected_source
    if expectedSource ~= nil and target.Source ~= expectedSource then
        return createOutcome(
            operation.operation_id,
            false,
            'Script source changed since the plan was created. Refresh context and re-plan.',
            {}
        )
    end

    local ok, err = pcall(function()
        local updateOk = pcall(function()
            ScriptEditorService:UpdateSourceAsync(target, function()
                return operation.payload.script_source
            end)
        end)
        if not updateOk then
            target.Source = operation.payload.script_source
        end
    end)
    if not ok then
        return createOutcome(operation.operation_id, false, tostring(err), {})
    end

    return createOutcome(
        operation.operation_id,
        true,
        'Patched script source.',
        { operation.target_path }
    )
end

local function runPlaytest(operation)
    local payload = operation.payload or {}
    local durationSeconds = tonumber(payload.duration_seconds) or 0
    local ok, err = pcall(function()
        local runMethod = TestService.Run
        if type(runMethod) ~= 'function' then
            error('TestService.Run is not available in this Studio context.')
        end
        runMethod(TestService)
        if durationSeconds > 0 then
            task.wait(durationSeconds)
        end
    end)

    if not ok then
        return createOutcome(operation.operation_id, false, tostring(err), {})
    end

    return createOutcome(operation.operation_id, true, 'Started playtest run.', {})
end

local function collectOutput(operation)
    return createOutcome(
        operation.operation_id,
        true,
        'Output is available through snapshot sync.',
        {}
    )
end

local function createInstance(operation)
    local parent = InstancePath.findByPath(operation.payload.parent_path)
    if parent == nil then
        return createOutcome(operation.operation_id, false, 'Parent path not found.', {})
    end

    local instance = Instance.new(operation.payload.class_name)
    instance.Name = operation.payload.name
    instance.Parent = parent

    local properties = operation.payload.properties or {}
    for propertyName, value in pairs(properties) do
        pcall(function()
            instance[propertyName] = value
        end)
    end

    return createOutcome(operation.operation_id, true, 'Created instance.', {
        InstancePath.getPath(instance),
    })
end

local function updateProperties(operation)
    local target = InstancePath.findByPath(operation.target_path)
    if target == nil then
        return createOutcome(operation.operation_id, false, 'Target not found.', {})
    end

    for propertyName, value in pairs(operation.payload.properties) do
        local ok, err = pcall(function()
            target[propertyName] = value
        end)
        if not ok then
            return createOutcome(operation.operation_id, false, tostring(err), {})
        end
    end

    return createOutcome(
        operation.operation_id,
        true,
        'Updated properties.',
        { operation.target_path }
    )
end

local function reparentInstance(operation)
    local target = InstancePath.findByPath(operation.target_path)
    local newParent = InstancePath.findByPath(operation.payload.new_parent_path)
    if target == nil or newParent == nil then
        return createOutcome(operation.operation_id, false, 'Target or new parent not found.', {})
    end

    target.Parent = newParent
    return createOutcome(operation.operation_id, true, 'Reparented instance.', {
        InstancePath.getPath(target),
    })
end

local function deleteInstance(operation)
    local target = InstancePath.findByPath(operation.target_path)
    if target == nil then
        return createOutcome(operation.operation_id, false, 'Target not found.', {})
    end

    target:Destroy()
    return createOutcome(
        operation.operation_id,
        true,
        'Deleted instance.',
        { operation.target_path }
    )
end

local function createCheckpoint(operation)
    local label = operation.payload.label or ('checkpoint-' .. operation.operation_id)
    ChangeHistoryService:SetWaypoint(label)
    return createOutcome(operation.operation_id, true, 'Checkpoint waypoint created.', {})
end

local function rollbackCheckpoint(operation)
    local checkpointId = tostring(operation.payload.checkpoint_id)
    local targetIndex = nil

    for index, checkpoint in ipairs(appliedCheckpoints) do
        if checkpoint.checkpoint_id == checkpointId then
            targetIndex = index
        end
    end

    if targetIndex == nil then
        return createOutcome(
            operation.operation_id,
            false,
            string.format('Checkpoint %s is not available in this plugin session.', checkpointId),
            {}
        )
    end

    local undoSteps = (#appliedCheckpoints - targetIndex) * 2 + 1
    for _ = 1, undoSteps do
        local ok, err = pcall(function()
            ChangeHistoryService:Undo()
        end)
        if not ok then
            return createOutcome(operation.operation_id, false, tostring(err), {})
        end
    end

    while #appliedCheckpoints >= targetIndex do
        table.remove(appliedCheckpoints)
    end

    return createOutcome(
        operation.operation_id,
        true,
        string.format('Rolled back to checkpoint %s.', checkpointId),
        {}
    )
end

local handlers = {
    apply_script_patch = applyScriptPatch,
    create_instance = createInstance,
    run_playtest = runPlaytest,
    collect_output = collectOutput,
    update_properties = updateProperties,
    reparent_instance = reparentInstance,
    delete_instance = deleteInstance,
    create_checkpoint = createCheckpoint,
    rollback_checkpoint = rollbackCheckpoint,
}

function OperationApplier.applyBatch(batch)
    local operations = batch.operations or batch
    local outcomes = {}
    local mutating = false
    local checkpointId = batch.checkpoint_id

    for _, operation in ipairs(operations) do
        if isMutating(operation.kind) then
            mutating = true
            break
        end
    end

    if mutating then
        ChangeHistoryService:SetWaypoint(
            checkpointId ~= nil and ('CodeRoblox checkpoint ' .. checkpointId)
                or 'CodeRoblox before batch'
        )
    end

    for _, operation in ipairs(operations) do
        local handler = handlers[operation.kind]
        if handler == nil then
            table.insert(
                outcomes,
                createOutcome(
                    operation.operation_id,
                    false,
                    'Unsupported operation for plugin.',
                    {}
                )
            )
        else
            table.insert(outcomes, handler(operation))
        end
    end

    if mutating then
        ChangeHistoryService:SetWaypoint('CodeRoblox after batch')
        if checkpointId ~= nil then
            table.insert(appliedCheckpoints, {
                checkpoint_id = checkpointId,
                batch_id = batch.batch_id,
            })
        end
    end

    return outcomes
end

return OperationApplier
