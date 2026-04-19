local Selection = game:GetService('Selection')
local LogService = game:GetService('LogService')

local InstancePath = require(script.Parent.InstancePath)

local SnapshotBuilder = {}

local PROJECT_SERVICES = {
    'Workspace',
    'ReplicatedStorage',
    'ServerScriptService',
    'ServerStorage',
    'StarterPlayer',
    'StarterGui',
    'StarterPack',
    'ReplicatedFirst',
    'Lighting',
    'SoundService',
}

local OVERVIEW_DEPTH = 2
local SELECTION_DEPTH = 3

local function canReadSource(instance)
    return instance:IsA('LuaSourceContainer')
end

local function captureNode(instance, depth, selectedPaths)
    local children = instance:GetChildren()
    local node = {
        path = InstancePath.getPath(instance),
        name = instance.Name,
        class_name = instance.ClassName,
        child_count = #children,
        is_selected = selectedPaths[InstancePath.getPath(instance)] == true,
        children = {},
    }

    if canReadSource(instance) then
        local ok, source = pcall(function()
            return instance.Source
        end)
        if ok then
            node.script_source = source
        end
    end

    if depth > 0 then
        for _, child in ipairs(children) do
            table.insert(node.children, captureNode(child, depth - 1, selectedPaths))
        end
    end

    return node
end

local function collectScriptDocuments(instance, documents)
    if canReadSource(instance) then
        local ok, source = pcall(function()
            return instance.Source
        end)
        if ok then
            table.insert(documents, {
                path = InstancePath.getPath(instance),
                name = instance.Name,
                class_name = instance.ClassName,
                source = source,
            })
        end
    end

    for _, child in ipairs(instance:GetChildren()) do
        collectScriptDocuments(child, documents)
    end
end

local function getProjectRoots()
    local roots = {}

    for _, serviceName in ipairs(PROJECT_SERVICES) do
        local ok, service = pcall(function()
            return game:GetService(serviceName)
        end)
        if ok and service ~= nil then
            table.insert(roots, service)
        end
    end

    return roots
end

local function serializeLogEntry(entry)
    if type(entry) ~= 'table' then
        return nil
    end

    local messageType = entry.messageType or entry.MessageType or 'Output'
    local message = entry.message or entry.Message or ''
    local timestamp = entry.timestamp or entry.Timestamp or 0
    return {
        message = tostring(message),
        message_type = tostring(messageType),
        timestamp = tonumber(timestamp) or 0,
    }
end

local function captureOutput()
    local entries = {}
    local diagnostics = {}
    local ok, history = pcall(function()
        return LogService:GetLogHistory()
    end)

    if not ok or type(history) ~= 'table' then
        return entries, diagnostics
    end

    for _, rawEntry in ipairs(history) do
        local entry = serializeLogEntry(rawEntry)
        if entry ~= nil then
            table.insert(entries, entry)
            if string.find(entry.message_type, 'Error') ~= nil then
                table.insert(diagnostics, {
                    severity = 'error',
                    source = 'roblox_output',
                    message = entry.message,
                    timestamp = entry.timestamp,
                })
            elseif string.find(entry.message_type, 'Warning') ~= nil then
                table.insert(diagnostics, {
                    severity = 'warning',
                    source = 'roblox_output',
                    message = entry.message,
                    timestamp = entry.timestamp,
                })
            end
        end
    end

    return entries, diagnostics
end

function SnapshotBuilder.buildSnapshot()
    local selected = Selection:Get()
    local selectedPaths = {}
    local nodes = {}
    local selectionPaths = {}
    local selectionNodes = {}
    local scriptDocuments = {}
    local outputLogs, diagnostics = captureOutput()

    for _, instance in ipairs(selected) do
        selectedPaths[InstancePath.getPath(instance)] = true
    end

    for _, root in ipairs(getProjectRoots()) do
        table.insert(nodes, captureNode(root, OVERVIEW_DEPTH, selectedPaths))
        collectScriptDocuments(root, scriptDocuments)
    end

    for _, instance in ipairs(selected) do
        table.insert(selectionPaths, InstancePath.getPath(instance))
        table.insert(selectionNodes, captureNode(instance, SELECTION_DEPTH, selectedPaths))
    end

    return {
        captured_at = DateTime.now():ToIsoDate(),
        project_name = game.Name,
        selection_paths = selectionPaths,
        nodes = nodes,
        selection_nodes = selectionNodes,
        script_documents = scriptDocuments,
        diagnostics = diagnostics,
        metadata = {
            root_service_count = #nodes,
            selected_count = #selectionPaths,
            script_count = #scriptDocuments,
            output_logs = outputLogs,
        },
    }
end

return SnapshotBuilder
