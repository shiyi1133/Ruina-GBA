/* Selective freestanding adaptation of EasyRPG Player 0.8.1.1:
 * src/algo.cpp and src/game_actor.cpp. Original copyright notices are retained
 * with the pinned reference files in third_party/Player/. GPL-3.0-or-later.
 * RM2000 major-updated, non-English profile, matching this game's EasyRPG
 * auto-detection. RPG2003 rows/percentage costs are not substituted.
 */
#include "rm2k_rules.h"

int rm2k_turn_matches(int turn,int base,int multiple){return turn>=base&&(multiple?(turn-base)%multiple==0:turn==base);}
int rm2k_fatigue(int hp,int max_hp,int mp,int max_mp){
    double n;if(max_hp<=0)return 0;if(max_mp==0)max_mp=1;n=100.0f*(((double)hp/max_hp*2.0+(double)mp/max_mp)/3.0f);return 100-(int)(n+0.5);
}
int rm2k_chip_index(int n){
    if(n>=0&&n<2000)return n/1000;
    if(n>=2000&&n<3000)return 2;
    if(n>=3000&&n<3150)return 3+(n-3000)/50;
    if(n>=4000&&n<4600)return 6+(n-4000)/50;
    if(n>=5000&&n<5144)return 18+n-5000;
    if(n>=10000&&n<10144)return 162+n-10000;
    return 0;
}
int rm2k_simulated_base(int attack,int defense_rate,int spirit_rate,int defense,int spirit){
    int n=attack-defense*defense_rate/400-spirit*spirit_rate/800;return n>0?n:0;
}
int rm2k_battle_page(const Rm2kBattleCondition*c,int turn,int enemy_hp,int enemy_max_hp,int actor_hp,int actor_max_hp){
    int f=c->flags&1023,n;if(!f)return 0;
    if((f&1)&&!c->switch_a)return 0;
    if((f&2)&&!c->switch_b)return 0;
    if((f&4)&&c->variable<c->threshold)return 0;
    if((f&8)&&!rm2k_turn_matches(turn,c->turn_b,c->turn_a))return 0;
    if(f&32){if(enemy_hp<0||enemy_max_hp<=0)return 0;n=100*enemy_hp/enemy_max_hp;if(n<c->enemy_min||n>c->enemy_max)return 0;}
    if(f&64){if(actor_hp<0||actor_max_hp<=0)return 0;n=100*actor_hp/actor_max_hp;if(n<c->actor_min||n>c->actor_max)return 0;}
    /* Fatigue/individual-turn/command flags are RPG2003-only. RM2000
     * considers them triggers but does not evaluate their conditions. */
    return 1;
}
int rm2k_compare(int a,int b,int op){
    switch(op){case 0:return a==b;case 1:return a>=b;case 2:return a<=b;
    case 3:return a>b;case 4:return a<b;case 5:return a!=b;default:return 0;}
}
int rm2k_variable_op(int old,int value,int op){
    long long n=old;
    switch(op){case 0:n=value;break;case 1:n+=value;break;case 2:n-=value;break;
    case 3:n*=value;break;case 4:if(value)n/=value;break;case 5:n=value?old%value:0;break;}
    return n>999999?999999:n< -999999?-999999:(int)n;
}
int rm2k_exp(int initial_base,int initial_inflation,int correction,int level){
    double base=initial_base,inflation=1.5+initial_inflation*0.01;
    int total=0,i;
    for(i=level;i>=1;i--){
        total+=(int)(correction+base);
        if(total>=999999)return 999999;
        base*=inflation;
        inflation=((level+1)*0.002+0.8)*(inflation-1)+1;
    }
    return total;
}
int rm2k_normal_base(int attack,int defense){
    int n=attack/2-defense/4;return n>0?n:0;
}
int rm2k_skill_base(int power,int physical,int magical,int attack,int spirit,
                   int defense,int target_spirit,int hostile,int ignore_defense){
    int n=power+physical*attack/20+magical*spirit/40;
    if(hostile&&!ignore_defense)n-=physical*defense/40+magical*target_spirit/80;
    return n>0?n:0;
}
int rm2k_skill_cost(int cost,int half){return (cost+(half!=0))/(half?2:1);}
int rm2k_variance_range(int base,int variance){
    int n;if(variance<=0||base<=0)return 0;n=variance*base/10;return n>0?n:1;
}
int rm2k_variance(int base,int variance,int roll){
    int n=rm2k_variance_range(base,variance);
    return n?base+roll-n/2:base;
}
int rm2k_defend(int damage,int defending,int strong){
    if(defending){damage/=2;if(strong)damage/=2;}return damage;
}
