#include "sushi_printer.h"

#include <iostream>

void print_sushi(std::ostream& output, int times) {
    for (int count = 0; count < times; ++count) {
        output << "sushi\n";
    }
}

int main() {
    print_sushi(std::cout, 3);
    return 0;
}
