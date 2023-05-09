json = require "json"

-- global var
processHandleFunscriptCopilot = nil
status = "Copilot not running"
updateCounter = 0


function get_platform()
    if ofs.ExtensionDir():find("^/home/") ~= nil then
        return "Linux"
    else
        return "Windows"
    end
end

platform = get_platform()


function binding.start_funscript_copilot()
    if processHandleFunscriptCopilot then
        print('Funscript Copilot already running')
        return
    end

    scriptIdx = ofs.ActiveIdx()
    local video = player.CurrentVideo()

    print("video: ", video)
    print("currentScriptIdx: ", scriptIdx)

    local cmd = ""
    local args = {}

    if platform == "Linux" then
        cmd = ofs.ExtensionDir() .. "/nix_wrapper.sh"
    else
        print("ERROR: Platform Not Implemented (", platform, ")")
        return
    end

    table.insert(args, "--input")
    table.insert(args, video)

    print("cmd: ", cmd)
    print("args: ", table.unpack(args))

    processHandleFunscriptCopilot = Process.new(cmd, table.unpack(args))

    status = "Copilot running"
end


function ws_receive(soruce, message)
    print("ws receive", source, message)
end


function init()
    print("OFS Version:", ofs.Version())
    print("Detected OS: ", platform)
end


function update(delta)
    updateCounter = updateCounter + 1
    if processHandleFunscriptCopilot and not processHandleFunscriptCopilot:alive() then
        processHandleFunscriptCopilot = nil
        status = "Copilot not running"
    end
end


function gui()
    ofs.Text("Status: "..status)
    ofs.Separator()
    ofs.Text("Action:")

    ofs.SameLine()
    if not processHandleFunscriptCopilot then
        if ofs.Button("Start Copilot") then
            binding.start_funscript_copilot()
        end
    else
        if ofs.Button("Kill Copilot") then
            if platform == "Linux" then
                os.execute("pkill -f python3")
            end
        end
    end
end
