#ifndef RUINA_BORROWED_COMMANDS_H
#define RUINA_BORROWED_COMMANDS_H
#include "lcf.h"
/* Only read-only control/variable opcodes with at most eight operand slots
 * use this view. Large UI commands retain their owned parameter arrays. */
typedef struct {LcfCommand command;ru32 original_offset,advance;int values[8];} BorrowedCommand;
extern const BorrowedCommand borrowed_commands[];
extern const unsigned short borrowed_command_index[];
extern const ru32 borrowed_command_hash_mask;
const BorrowedCommand*LCF_HOT lcf_borrow_command(LcfReader*r);
#endif
