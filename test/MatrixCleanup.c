/* Matrix ownership regression with allocator accounting and fault injection.
   The legacy mode only runs previously supported build/factor/solve/destroy. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "system_matrix.h"
#include <stdint.h>
static long fail_at = -1, allocations;
static size_t live_bytes, live_blocks;
#define SLOTS 262144
static struct { void *ptr; size_t size; } tracked[SLOTS];
#define TOMBSTONE ((void *)(uintptr_t)1)
static size_t slot(void *p) { return ((uintptr_t)p >> 4) % SLOTS; }
static void remember(void *p, size_t size) {
    if (!p) return;
    size_t i=slot(p);
    while (tracked[i].ptr && tracked[i].ptr!=TOMBSTONE) i=(i+1)%SLOTS;
    tracked[i].ptr=p;tracked[i].size=size;live_bytes+=size;live_blocks++;
}
static void forget(void *p) {
    if (!p) return;
    size_t i=slot(p);
    while (tracked[i].ptr) {
        if (tracked[i].ptr==p) {
            live_bytes-=tracked[i].size;live_blocks--;
            tracked[i].ptr=TOMBSTONE;return;
        }
        i=(i+1)%SLOTS;
    }
}
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
void *__real_realloc(void *,size_t);
void __real_free(void *);
void *__wrap_malloc(size_t size) {
    if (fail_at > 0 && ++allocations == fail_at) return NULL;
    void *p=__real_malloc(size);remember(p,size);return p;
}
void *__wrap_calloc(size_t n,size_t size) {
    void *p=__real_calloc(n,size);remember(p,n*size);return p;
}
void *__wrap_realloc(void *p,size_t size) {
    void *q=__real_realloc(p,size);
    if (q || size==0) {forget(p);remember(q,size);}
    return q;
}
void __wrap_free(void *p) {forget(p);__real_free(p);}
static void fill(SystemMatrix_t *m, double diagonal) {
    for (int i = 0; i < m->Size; ++i) {
        m->ColumnPointers[i] = i;
        m->RowIndices[i] = i;
        m->Values[i] = diagonal;
    }
    m->ColumnPointers[m->Size] = m->Size;
}
static void solve(SystemMatrix_t *m, double diagonal) {
    double *rhs = malloc(sizeof(double) * m->Size);
    for (int i=0; i<m->Size; ++i) rhs[i] = diagonal * (i+1);
    SuperMatrix b;
    dCreate_Dense_Matrix(&b,m->Size,1,rhs,m->Size,SLU_DN,SLU_D,SLU_GE);
    assert(solve_sparse_linear_system(m,&b)==TDICE_SUCCESS);
    for (int i=0; i<m->Size; ++i) assert(fabs(rhs[i]-(i+1))<1e-10);
    Destroy_SuperMatrix_Store(&b);
    free(rhs);
}
int main(int argc,char **argv) {
    int legacy = argc > 1 && strcmp(argv[1],"legacy")==0;
    int iterations = argc > 2 ? atoi(argv[2]) : 1000;
    SystemMatrix_t m;
    if (!legacy) {
        system_matrix_init(&m);
        system_matrix_destroy(&m);
        system_matrix_destroy(&m);
        /* Each allocation owned directly by system_matrix_build; allocation
           failures inside SuperLU itself abort, so are not injected here. */
        int sites[] = {1,2,3,5,6,7,8,9};
        for (unsigned j=0; j<sizeof(sites)/sizeof(sites[0]); ++j) {
            system_matrix_init(&m);
            allocations=0;fail_at=sites[j];
            assert(system_matrix_build(&m,32,32,1)==TDICE_FAILURE);
            fail_at=-1;
            assert(m.SLUMatrix_A.Store==NULL && m.Values==NULL);
            system_matrix_destroy(&m);
        }
        system_matrix_init(&m);
        assert(system_matrix_build(&m,32,32,1)==TDICE_SUCCESS);
        system_matrix_destroy(&m); /* built but never factored */
        system_matrix_init(&m);
        assert(system_matrix_build(&m,32,32,1)==TDICE_SUCCESS);
        assert(allocate_L_Matrix(&m)==TDICE_SUCCESS);
        assert(allocate_U_Matrix(&m)==TDICE_SUCCESS);
        fill(&m,2);
        assert(do_factorization(&m)==TDICE_SUCCESS);
        solve(&m,2);
        fill(&m,3);
        assert(do_factorization(&m)==TDICE_SUCCESS);
        solve(&m,3);
        m.SLU_Options.refact=YES;
        fill(&m,4);
        assert(do_factorization(&m)==TDICE_SUCCESS);
        solve(&m,4);
        system_matrix_destroy(&m);
        system_matrix_init(&m);
        assert(system_matrix_build(&m,32,32,1)==TDICE_SUCCESS);
        fill(&m,0);
        assert(do_factorization(&m)==TDICE_FAILURE);
        fill(&m,2);
        assert(do_factorization(&m)==TDICE_SUCCESS); /* retry after failure */
        solve(&m,2);
        system_matrix_destroy(&m);
        system_matrix_init(&m);
        assert(system_matrix_build(&m,32,32,1)==TDICE_SUCCESS);
        fill(&m,0);
        assert(do_factorization(&m)==TDICE_FAILURE);
        system_matrix_destroy(&m); /* partially factored singular matrix */
    }
    size_t initial_bytes=live_bytes;
    for (int i=0;i<iterations;++i) {
        system_matrix_init(&m);
        assert(system_matrix_build(&m,512,512,1)==TDICE_SUCCESS);
        fill(&m,2+(i%3));
        assert(do_factorization(&m)==TDICE_SUCCESS);
        solve(&m,2+(i%3));
        system_matrix_destroy(&m);
    }
    printf("LIVE bytes=%zu blocks=%zu growth=%zd\n",live_bytes,live_blocks,(long)(live_bytes-initial_bytes));
    if (!legacy && live_blocks) {
        for (size_t j=0;j<SLOTS;++j) if (tracked[j].ptr && tracked[j].ptr!=TOMBSTONE) {
            fprintf(stderr,"RESIDUAL size=%zu\n",tracked[j].size);
        }
    }
    if (!legacy) assert(live_bytes==0 && live_blocks==0);
    printf("Matrix cleanup passed: %d cycles; legacy=%d\n",iterations,legacy);
    return 0;
}
