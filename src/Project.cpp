#include "Project.h"
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QSaveFile>
#include <QSet>
#include <QTextStream>

namespace {
constexpr auto begin = "<!-- agents-opencode:begin -->";
constexpr auto end = "<!-- agents-opencode:end -->";
QString textFile(const QString& filename) {
    QFile f(filename);
    return f.open(QIODevice::ReadOnly) ? QString::fromUtf8(f.readAll()) : QString();
}
QJsonObject object(const QJsonObject& o,const QString& k){return o.value(k).toObject();}
QString setting(const QJsonObject& o,const QString& k,const QString& defaultValue="ask"){
    return o.value(k).toString(defaultValue);
}
QJsonObject glob(const QString& star) { return {{"*",star}}; }
bool readOnlyRole(const QString& r) {
    return r=="code-reviewer" || r=="image-analyst" || r=="system-architect" || r=="technical-educator";
}
QJsonObject agentPermission(const ProjectConfig& c,const QString& name){
    const QJsonObject tools=object(c.policy,"tools");
    const QJsonObject git=object(c.policy,"git");
    const QJsonObject network=object(c.policy,"network");
    QJsonObject bash{{"*",setting(tools,"bash")},
      {"git status*","allow"},{"git diff*","allow"},{"git log*","allow"},
      {"git fetch*",setting(git,"fetch","deny")},{"git pull*",setting(git,"pull","deny")},
      {"git commit*",setting(git,"commit","deny")},{"git merge*",setting(git,"merge","deny")},
      {"git push*",setting(git,"push","deny")},
      {"git push --force*",setting(git,"force_push","deny")},{"git push -f *",setting(git,"force_push","deny")},
      {"git reset --hard*","deny"},{"git clean -f*","deny"},
      {"sudo *","deny"},{"su *","deny"},{"pkexec *","deny"},
      {"flashrom *","deny"},{"dfu-util *","deny"},{"openocd *","deny"},
      {"uhd_image_loader *","deny"}};
    QJsonObject read{{"*",setting(tools,"read","allow")},{"*.env","ask"},{"*.env.*","ask"}};
    QJsonObject p{{"read",read},{"edit",setting(tools,"edit","ask")},{"bash",bash},
       {"webfetch",setting(network,"internet")},{"websearch",setting(network,"internet")},
       {"external_directory",glob(setting(tools,"external_directory","deny"))},
       {"task","deny"}};
    // Filesystem entries are advisory intent unless enforced by actual OpenCode rules and OS permissions.
    if(name=="orchestrator"){
        p["edit"]=QJsonObject{{"*","deny"},{".local-work/**","allow"},{".agents-opencode/logs/**","allow"}};
        QJsonObject tasks{{"*","deny"}};
        for(const auto& r:c.agents) if(r!="orchestrator") tasks[r]="allow";
        p["task"]=tasks;
    }
    if(readOnlyRole(name)) {p["edit"]="deny";p["bash"]="deny";}
    auto overrides=object(object(c.policy,"agent_overrides"),name);
    for(auto it=overrides.begin();it!=overrides.end();++it){
        const QString k=it.key(), v=it.value().toString();
        if(k=="task")continue;
        if(readOnlyRole(name) && (k=="bash"||k=="edit") && v!="deny") continue;
        if(v!="inherit" && (v=="deny"||v=="ask"||v=="allow")) {
            // Keep the default protection for environment/credential files even
            // when an agent gets a read override.
            if(k=="read" && v!="deny")
                p[k]=QJsonObject{{"*",v},{"*.env","ask"},{"*.env.*","ask"}};
            else p[k]=v;
        }
    }
    return p;
}
bool validate(const ProjectConfig& c,QString& error){
    if(c.agents.empty()){error="Markera minst en agent.";return false;}
    if(!c.agents.contains("orchestrator")){error="Orchestrator måste finnas för denna teamuppsättning.";return false;}
    QSet<QString> known; for(const auto& v:Project::availableRoles()) known.insert(v);
    for(const auto& role:c.agents){
        if(!known.contains(role)){error="Okänd agentroll: "+role;return false;}
        if(c.models.value(role).toString().trimmed().isEmpty()){
            error="Välj modell för "+role;return false;
        }
    }
    const QJsonObject network=object(c.policy,"network");
    if(!QStringList{"allow","ask","deny"}.contains(network.value("internet").toString())){
        error="Ogiltig internetpolicy.";return false;
    }
    return true;
}
bool checkSafe(const QString& root,const QString& relative,QString& error){
    // Explicitly reject symlinks at any parent or final managed path.
    auto current=QDir(root).absolutePath();
    for(const auto& segment: relative.split('/')){
        if(segment==".."||segment.isEmpty()||segment==".") {error="Ogiltig sökväg";return false;}
        current=QDir(current).filePath(segment);
        if(QFileInfo(current).isSymLink()){
            error="Vägrar skriva via symbolisk länk: "+current;return false;
        }
    }
    return true;
}
bool writeFile(const QString& full,const QByteArray& bytes,QString& error){
    if(!QDir().mkpath(QFileInfo(full).absolutePath())){error="Kunde inte skapa katalog: "+full;return false;}
    QSaveFile f(full);
    if(!f.open(QIODevice::WriteOnly)){error=f.errorString()+": "+full;return false;}
    if(f.write(bytes)!=bytes.size()){error="Kunde inte skriva "+full;f.cancelWriting();return false;}
    if(!f.commit()){error="Kunde inte slutföra "+full;return false;}
    return true;
}
QString profile(const QString& role){
    const QString original=textFile(":/agents/"+role+".md");
    // Preserve the real specialist description and full audited instructions.
    // Replacing the original front matter with a generic description makes
    // agents harder for the orchestrator to select accurately.
    if(original.startsWith("---\n")) return original;
    return QString("---\ndescription: Specialist agent %1\nmode: %2\n---\n\n%3\n")
        .arg(role,role=="orchestrator"?"primary":"subagent",original);
}

QString instructionBlock(){
    return QString::fromUtf8(begin)+"\n# Agentteam\n\nLäs `PROJECT_BRIEF.md`, `.agents-opencode/TEAM_REGISTRY.md`, `.opencode/team/TEAM_RULES.md` och `.opencode/team/WORKFLOW.md`. Orkestreraren ska kontrollera vilka agenter som faktiskt kan anropas, tilldela specialister deras uppgifter och dokumentera verifieringsunderlag. Behörighetspolicyn i `AGENT_ACCESS_POLICY.json` kan innehålla rådgivande begränsningar som inte tekniskt upprätthålls.\n"+end;
}
QString registry(const ProjectConfig& c){
    QString s="# Agentteam\n\nGenererat av agents-opencode GUI. Uppgifterna är konfigurationsavsikt, inte körstatus.\n\n| Agent | Modell | Roll |\n|---|---|---|\n";
    for(const auto& r:c.agents) s+="| `"+r+"` | `"+c.models.value(r).toString().replace('|',"\\|")+"` | "+(r=="orchestrator"?"Coordinator":"Specialist")+" |\n";
    s+="\nOrkestreraren ska bekräfta faktisk tillgänglighet innan delegering.\n";
    return s;
}
QJsonObject decodeJson(const QString& file, QString& error) {
    if(!QFile::exists(file))return {};
    QJsonParseError pe;
    const auto doc=QJsonDocument::fromJson(textFile(file).toUtf8(),&pe);
    if(pe.error!=QJsonParseError::NoError||!doc.isObject()){
        error="Kunde inte läsa JSON: "+file+" ("+pe.errorString()+")";
        return {};
    }
    return doc.object();
}
}

namespace Project {
QStringList availableRoles(){
    return QDir(":/agents").entryList({"*.md"},QDir::Files).replaceInStrings(".md","");
}
QJsonObject defaultPolicy(){
    return QJsonObject{
        {"tools",QJsonObject{{"read","allow"},{"edit","ask"},{"bash","ask"},{"webfetch","ask"},{"websearch","ask"},{"external_directory","deny"}}},
        {"git",QJsonObject{{"fetch","ask"},{"pull","ask"},{"commit","ask"},{"push","deny"},{"merge","ask"},{"force_push","deny"},{"destructive","deny"}}},
        {"network",QJsonObject{{"internet","ask"},{"allow",QJsonArray{}},{"deny",QJsonArray{}}}},
        {"paths",QJsonArray{}},{"paths_deny",QJsonArray{}},{"shares",QJsonArray{}},{"shares_deny",QJsonArray{}},
        {"devices",QJsonArray{}},{"hardware",QJsonObject{{"usb","deny"},{"firmware","deny"}}},
        {"agent_overrides",QJsonObject{}}, {"unattended",false}
    };
}
ProjectConfig defaultConfig(){
    return {{"orchestrator"},{},defaultPolicy(),QJsonObject{{"mode","local"},{"remote","origin"},{"ssh_port",22},{"branch","main"}},
        "# Projektbeskrivning\n\nBeskriv vad agenterna ska utveckla, krav, begränsningar och acceptanskriterier.\n"};
}
QJsonObject toJson(const ProjectConfig& c){
    QJsonArray arr;for(const auto& r:c.agents)arr.append(r);
    return {{"version",3},{"agents",arr},{"models",c.models},{"policy",c.policy},{"git",c.git}};
}
bool load(const QString& root,ProjectConfig& data,QString& error){
    const QString path=QDir(root).filePath(".agents-opencode/config.json");
    if(!QFile::exists(path)){
        data=defaultConfig();
        QString b=textFile(QDir(root).filePath("PROJECT_BRIEF.md"));
        if(!b.isEmpty())data.brief=b;
        return true;
    }
    auto d=decodeJson(path,error);
    if(!error.isEmpty())return false;
    if(d.value("version").toInt()!=3){error="Befintligt konfigurationsformat stöds inte. Säkerhetskopiera och migrera manuellt.";return false;}
    data=defaultConfig();data.agents.clear();
    for(const auto& v:d.value("agents").toArray())data.agents.append(v.toString());
    data.models=d.value("models").toObject();
    data.policy=d.value("policy").toObject();
    data.git=d.value("git").toObject();
    QString b=textFile(QDir(root).filePath("PROJECT_BRIEF.md"));
    if(!b.isEmpty())data.brief=b;
    return true;
}
QJsonObject openCodeConfig(const QString& root,const ProjectConfig& c,QString& error){
    QJsonObject d=decodeJson(QDir(root).filePath("opencode.json"),error);
    if(!error.isEmpty())return {};
    if(d.contains("agents") || d.contains("permissions")){
        error="OpenCode 2-konfiguration upptäckt. Denna GUI-version stödjer endast OpenCode 1.x.";
        return {};
    }
    QJsonObject a=d.value("agent").toObject();
    if(d.contains("agent")&&!d.value("agent").isObject()) {error="Befintligt opencode.json har ogiltigt agent-fält.";return {};}
    // Remove only agents from an earlier managed configuration that the user deselected.
    QString olderr;
    ProjectConfig previous;
    if(QFile::exists(QDir(root).filePath(".agents-opencode/config.json")) && load(root,previous,olderr)){
        for(const auto& r:previous.agents) if(!c.agents.contains(r))a.remove(r);
    }
    for(const auto& r:c.agents){
        a[r]=QJsonObject{{"model",c.models.value(r).toString()},{"mode",r=="orchestrator"?"primary":"subagent"}, {"permission",agentPermission(c,r)}};
    }
    d["agent"]=a;
    if(!d.contains("$schema"))d["$schema"]="https://opencode.ai/config.json";
    d["default_agent"]="orchestrator";
    return d;
}
QString preview(const QString& root,const ProjectConfig& c,QString& error){
    if(!validate(c,error))return {};
    auto oc=openCodeConfig(root,c,error);
    if(!error.isEmpty())return {};
    QString txt="=== .agents-opencode/config.json ===\n"+QString::fromUtf8(QJsonDocument(toJson(c)).toJson(QJsonDocument::Indented));
    txt+="\n=== opencode.json ===\n"+QString::fromUtf8(QJsonDocument(oc).toJson(QJsonDocument::Indented));
    txt+="\n=== Viktigt ===\nURL-filter, USB- och firmwarebegränsningar är avsiktsregler och inte ett OS-sandbox.\n";
    return txt;
}
bool save(const QString& root,const ProjectConfig& c,QString& error){
    if(!QDir(root).exists()){error="Projektmappen saknas.";return false;}
    if(!validate(c,error))return false;
    auto oc=openCodeConfig(root,c,error);
    if(!error.isEmpty())return false;
    QMap<QString,QByteArray> files;
    auto json=[](const QJsonObject& o){return QJsonDocument(o).toJson(QJsonDocument::Indented);};
    files.insert(".agents-opencode/config.json",json(toJson(c)));
    files.insert("opencode.json",json(oc));
    files.insert("AGENT_ACCESS_POLICY.json",json(c.policy));
    files.insert(".agents-opencode/TEAM_REGISTRY.md",registry(c).toUtf8());
    files.insert("PROJECT_BRIEF.md",c.brief.toUtf8());
    QString agents=textFile(QDir(root).filePath("AGENTS.md"));
    auto ib=instructionBlock();
    auto b=agents.indexOf(begin), e=agents.indexOf(end);
    if(b>=0 && e>b)agents.replace(b,e+QString::fromUtf8(end).size()-b,ib);
    else agents+="\n\n"+ib+"\n";
    files.insert("AGENTS.md",agents.toUtf8());
    for(const auto& n:c.agents)files.insert(".opencode/agents/"+n+".md",profile(n).toUtf8());
    for(const auto& n:{"TEAM_RULES.md","WORKFLOW.md","HANDOFF_TEMPLATE.md","ACCESS_RULES.md"}){
        const auto bytes=textFile(":/team/"+QString::fromLatin1(n));
        files.insert(".opencode/team/"+QString::fromLatin1(n),bytes.toUtf8());
    }
    QStringList removed;
    QString olderr; ProjectConfig previous;
    if(QFile::exists(QDir(root).filePath(".agents-opencode/config.json")) && load(root,previous,olderr)){
        for(const auto& r:previous.agents)if(!c.agents.contains(r))removed<<".opencode/agents/"+r+".md";
    }
    // Fully validate paths before any change.
    for(auto it=files.begin();it!=files.end();++it) if(!checkSafe(root,it.key(),error))return false;
    for(const auto& r:removed)if(!checkSafe(root,r,error))return false;
    // Back up ALL existing managed files before applying changes.
    QString stamp=QDateTime::currentDateTimeUtc().toString("yyyyMMdd-hhmmsszzz");
    QString backupBase=QDir(root).filePath(".agents-opencode/backups/"+stamp);
    if(!checkSafe(root,".agents-opencode/backups/"+stamp,error))return false;
    QStringList existing=files.keys()+removed;
    for(const auto& rel:existing){
        QString from=QDir(root).filePath(rel);
        if(QFile::exists(from)){
            QString to=QDir(backupBase).filePath(rel);
            if(!QDir().mkpath(QFileInfo(to).absolutePath())||!QFile::copy(from,to)){
                error="Backup misslyckades: "+from;return false;
            }
        }
    }
    auto rollback=[&](){
        bool ok=true;
        for(const auto& rel:existing){
            const QString destination=QDir(root).filePath(rel);
            const QString backup=QDir(backupBase).filePath(rel);
            if(QFile::exists(destination) && !QFile::remove(destination)) ok=false;
            if(QFile::exists(backup) && !QFile::copy(backup,destination)) ok=false;
        }
        return ok;
    };
    for(auto it=files.begin();it!=files.end();++it){
        if(!writeFile(QDir(root).filePath(it.key()),it.value(),error)){
            const bool restored=rollback();
            error+=restored?". Tidigare filer återställda.":". Återställ manuellt från: "+backupBase;
            return false;
        }
    }
    for(const auto& r:removed){
        if(QFile::exists(QDir(root).filePath(r)) && !QFile::remove(QDir(root).filePath(r))){
            const bool restored=rollback();
            error="Kunde inte ta bort avmarkerad agent: "+r;
            error+=restored?". Tidigare filer återställda.":". Återställ manuellt från: "+backupBase;
            return false;
        }
    }
    return true;
}
}
