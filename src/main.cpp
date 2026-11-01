#include "MainWindow.h"
#include <QApplication>
#include <QStyleFactory>
#include <QDir>

int main(int argc,char** argv){
    QApplication app(argc,argv);
    QApplication::setApplicationName("Agents OpenCode");
    QApplication::setOrganizationName("agents-opencode");
    QApplication::setApplicationVersion("3.1.0-beta.1");
    QApplication::setStyle(QStyleFactory::create("Fusion"));
    MainWindow window;
    window.show();
    return app.exec();
}
