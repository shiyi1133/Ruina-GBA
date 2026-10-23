#ifndef RUINA_RM2K_RULES_H
#define RUINA_RM2K_RULES_H
/* Allocation-free RM2000 rule adapter. Reference versions and hashes are in
 * third_party/sources.lock.json. No GBA hardware or game globals are used here.
 * Adapted from EasyRPG Player, GPL-3.0-or-later; see LICENSE and CREDITS.txt. */
int rm2k_compare(int a,int b,int op);
int rm2k_variable_op(int old,int value,int operation);
int rm2k_exp(int base,int inflation,int correction,int level);
int rm2k_normal_base(int attack,int defense);
int rm2k_skill_base(int power,int physical,int magical,int attack,int spirit,
                   int target_defense,int target_spirit,int hostile,int ignore_defense);
int rm2k_skill_cost(int cost,int half);
int rm2k_variance_range(int base,int variance);
int rm2k_variance(int base,int variance,int roll);
int rm2k_defend(int damage,int defending,int strong_defense);
int rm2k_turn_matches(int turn,int base,int multiple);
int rm2k_simulated_base(int attack,int defense_rate,int spirit_rate,int defense,int spirit);
typedef struct {
    int flags,switch_a,switch_b,variable,threshold,turn_a,turn_b;
    int enemy_min,enemy_max,actor_min,actor_max;
} Rm2kBattleCondition;
int rm2k_battle_page(const Rm2kBattleCondition*c,int turn,int enemy_hp,int enemy_max_hp,int actor_hp,int actor_max_hp);
int rm2k_chip_index(int chip_id);
int rm2k_fatigue(int hp,int max_hp,int mp,int max_mp);
#endif
