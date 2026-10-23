#include SHOP_SOURCE
#include <assert.h>
#include <stdio.h>
int main(void){
    unsigned bitmap[(MAX_ITEM+31)/32],seed=0x73686f70U,checked=0,trial;
    u16 expected[MAX_ITEM];int buying[5]={17,1,MAX_ITEM,300,17};
    for(trial=0;trial<1024;trial++){
        unsigned i,count=0,density=trial%101;
        for(i=0;i<(MAX_ITEM+31)/32;i++)bitmap[i]=0;
        for(i=1;i<=MAX_ITEM;i++){
            seed=seed*1664525U+1013904223U;
            if((seed>>8)%100<density){bitmap[(i-1)/32]|=1U<<((i-1)&31);expected[count++]=i;}
        }
        for(i=0;i<count;i++){assert(goods_id(bitmap,i,1)==expected[i]);checked++;}
        for(i=0;i<5;i++)assert(goods_id(buying,i,0)==buying[i]);
    }
    printf("{\"status\":\"pass\",\"subsets\":1024,\"sold_item_positions_checked\":%u,\"buy_order_and_duplicates_preserved\":true}\n",checked);
    return 0;
}
