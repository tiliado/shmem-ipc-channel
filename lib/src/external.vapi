[CCode(cheader_filename="sys/mman.h")]
private int shm_open(string name, int oflag, Posix.mode_t mode);

[CCode(cheader_filename="sys/mman.h")]
private int shm_unlink(string name);

[CCode(cname="sem_t", cheader_filename="semaphore.h")]
private struct Sem {
    [CCode(cname="sem_open")]
    public static Sem open(string name, int oflag, Posix.mode_t mode, uint value);

    [CCode(cname="sem_unlink")]
    public static int unlink(string name);

    [CCode(cname="sem_close")]
    public int sem_close();

    [CCode(cname="sem_post")]
    public int post();

    [CCode(cname="sem_wait")]
    public int wait();

    [CCode(cname="sem_trywait")]
    public int trywait();

    [CCode(cname="sem_init")]
    public int init(int pshared, uint value);

    [CCode(cname="sem_destroy")]
    public int destroy();
}
