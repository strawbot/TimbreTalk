#include <QtGui>
#include <QAction>
#include "MainWindow.h"

MainWindow::MainWindow() {

        // Creeam fereastra principala
    QWidget *window = new QWidget;
    setCentralWidget(window);

    // Creeam eticheta unde vom afisa titlul item-ului selectat
    // Implicit va avea un titlu predefinit
   infoLabel = new QLabel("Selectati un item va rog ");

    createActions();
    createMenus();

    // Creeam un layout pentru pozitionarea etichetei
    QHBoxLayout *layout = new QHBoxLayout;

    layout->addWidget(infoLabel);
    window->setLayout(layout);

    setWindowTitle("GUI");
    setMinimumSize(300, 300);
    resize(480,320);
}

void MainWindow::contextMenuEvent(QContextMenuEvent *event) {

    QMenu menu(this);
    menu.addAction(newAction);
    menu.addAction(openAction);
    menu.addAction(closeAction);
    menu.addAction(preferencesAction);
    menu.exec(event->globalPos());
}

void MainWindow::new_() {

    infoLabel->setText("A fost selectat : NEW");
}

void MainWindow::open() {

     infoLabel->setText("A fost selectat : OPEN");
}

void MainWindow::close() {

}

void MainWindow::preferences() {

     infoLabel->setText("A fost selectat : PREFERENCES");
}


void MainWindow::createActions()
{
    newAction = new QAction("New", this);
    connect(newAction, SIGNAL(triggered()), this, SLOT(new_()));

    openAction = new QAction("Open", this);
    connect(openAction, SIGNAL(triggered()), this, SLOT(open()));

    closeAction = new QAction("Close", this);
    connect(closeAction, SIGNAL(triggered()), this, SLOT(close()));

    preferencesAction = new QAction("Preferences", this);
    connect(preferencesAction, SIGNAL(triggered()), this, SLOT(preferences()));
}

void MainWindow::createMenus()
{
    // Creeaza sectiunea File
    fileMenu = new QMenu ("File");

    // Adauga actiunile new,open si close la sectiunea File
    fileMenu->addAction(newAction);
    fileMenu->addAction(openAction);
    fileMenu->addAction(closeAction);


    //  Creeaza sectiunea View
     viewMenu = new QMenu ("View");

    //Adauga actiunea preferences la sectiunea View
    viewMenu->addAction(preferencesAction);

    menuBar()->addMenu(fileMenu);
    menuBar()->addMenu(viewMenu);
}
